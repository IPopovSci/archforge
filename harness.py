"""Host-neutral compiler and verification commands. Run from the target repository root."""
import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import tomllib
from pathlib import Path
from typing import Annotated, Literal, Protocol
from xml.etree import ElementTree

from pydantic import BaseModel, ConfigDict, Field

INSTALL = Path(__file__).resolve().parent
BIN = Path(sys.executable).parent
Identifier = Annotated[str, Field(pattern=r"^[A-Z][A-Z0-9]*-[A-Z0-9-]+$")]


class Record(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)
    version: Literal[1]


class Ticket(Record):
    id: Identifier
    intent: str = Field(min_length=1)
    components: list[str] = Field(min_length=1)
    actions: list[Literal["extend_behavior", "fix_behavior"]] = Field(min_length=1)
    requirements: dict[Identifier, Annotated[str, Field(min_length=1)]] = Field(min_length=1)
    unknowns: list[str]


class Catalog(Record):
    revision: str
    modules: dict[str, str]


class Task(Record):
    ticket: Ticket
    revision: str
    scope: list[str]
    acceptance_file: str
    checks: list[str]
    evidence: list[dict]


class Receipt(Record):
    requirement_test_links: dict[Identifier, list[str]]


def run(*args, cwd=None, check=True):
    result = subprocess.run(args, cwd=cwd, capture_output=True, encoding="utf-8",
                            errors="replace", timeout=180)
    if check and result.returncode:
        raise ValueError((result.stdout + result.stderr)[-4000:])
    return result


def git(*args, cwd=None):
    return run("git", *args, cwd=cwd).stdout.strip()


def clean_revision(cwd=None):
    if git("status", "--porcelain", "--untracked-files=all", cwd=cwd):
        raise ValueError("Commit the attempt in its worktree before requesting revision-bound evidence.")
    return git("rev-parse", "HEAD", cwd=cwd)


def trail(*args):
    binary = BIN / ("node.exe" if os.name == "nt" else "node")
    return run(binary, INSTALL / "node_modules/@trailhq/trail-code/dist/bin/trail.js", *args).stdout


def catalog():
    revision = clean_revision()
    policy = tomllib.loads(Path("tach.toml").read_text())
    modules = {row["path"]: row["path"].replace(".", "/") + ".py" for row in policy["modules"]}
    roots = sorted({p.split("/")[0] for p in modules.values()} | {"tests"})
    flags = [arg for root in roots for arg in ("--only-dir", root)]
    trail("build", "--strict", "--no-gitignore", "--no-ignore", *flags)
    nodes = json.loads(Path("graft/.graph/wiring.json").read_text(encoding="utf-8"))["nodes"]
    observed = {n["path"] for n in nodes if n["kind"] == "file"}
    missing = set(modules.values()) - observed
    unmanaged = {p for p in observed if p.endswith(".py") and not p.startswith("tests/")
                 and not p.endswith("/__init__.py")} - set(modules.values())
    if missing or unmanaged:
        raise ValueError(f"Resolve policy/graph disagreement: missing={missing}, unmanaged={unmanaged}")
    return Catalog(version=1, revision=revision, modules=modules)


def get_context(query):
    if not query.strip() or len(query) > 1000 or query.startswith("-"):
        raise ValueError("Provide a short search phrase.")
    cat = catalog()
    hits = json.loads(trail("ask", query, ".", "--json", "--source", "-n", "6"))["hits"]
    return [dict(pointer=h["pointer"], title=h["title"][:120], code=h.get("code", "")[:650],
                 revision=cat.revision, reason="Trail query match") for h in hits if h.get("pointer")]


def compile_ticket(ticket):
    cat = catalog()
    if ticket.unknowns or set(ticket.components) - cat.modules.keys():
        raise ValueError("Resolve unknowns and component references before compilation.")
    acceptance = "tests/test_" + ticket.id.lower().replace("-", "_") + ".py"
    if Path(acceptance).exists():
        raise ValueError("Ticket needs a fresh acceptance test file.")
    task = Task(version=1, ticket=ticket, revision=cat.revision,
                scope=sorted({cat.modules[c] for c in ticket.components} | {acceptance}),
                acceptance_file=acceptance, checks=["tach", "pytest", "requirement links", "scope"],
                evidence=get_context(ticket.intent))
    if clean_revision() != cat.revision:
        raise ValueError("Source revision changed during compilation.")
    data = task.model_dump_json(indent=2).encode()
    digest = hashlib.sha256(data).hexdigest()
    path = Path(".harness/compiled") / (digest + ".json")
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("xb") as f:
            f.write(data)
    except FileExistsError:
        if path.read_bytes() != data:
            raise ValueError("Compiled artifact digest mismatch.")
    return {"contract": digest, "task": task.model_dump()}


def profile(paths):
    if not paths:
        return "FULL"
    if all(p == "README.md" or re.fullmatch(r"docs/usage/[\w-]+\.md", p) for p in paths):
        return "FAST"
    components = {p for p in paths if p.startswith("fixture/")}
    if len(components) <= 1 and all(p.endswith(".py") and p.startswith(("fixture/", "tests/")) for p in paths):
        return "STANDARD"
    return "FULL"


class DecisionProvider(Protocol):
    def decide(self, paths: list[str], allowed_actions: list[str]) -> dict: ...


class RuleProvider:
    def decide(self, paths, allowed_actions):
        action = profile(paths)
        if action not in allowed_actions:
            raise ValueError(f"Mandatory profile {action} is unavailable")
        return {"choice": action, "provider": "rules-v1", "scores": {action: 1},
                "evidence": paths}


def diff_paths(base, cwd=None):
    data = run("git", "diff", "--name-only", "--no-renames", "-z", base, "--", cwd=cwd).stdout
    extra = run("git", "ls-files", "--others", "--exclude-standard", "-z", cwd=cwd).stdout
    return sorted(set(filter(None, (data + extra).split("\0"))))


def verify(contract, attempt, receipt):
    if not re.fullmatch("[0-9a-f]{64}", contract):
        raise ValueError("Expected compiler digest.")
    data = (Path(".harness/compiled") / (contract + ".json")).read_bytes()
    if hashlib.sha256(data).hexdigest() != contract:
        raise ValueError("Compiled contract was modified.")
    task = Task.model_validate_json(data)
    revision = clean_revision(attempt)
    run("git", "merge-base", "--is-ancestor", task.revision, revision, cwd=attempt)
    paths = diff_paths(task.revision, attempt)
    problems = []
    if set(paths) - set(task.scope) or task.acceptance_file not in paths:
        problems.append("Scope violation or missing new acceptance file")
    links = receipt.requirement_test_links
    if set(links) != set(task.ticket.requirements):
        problems.append("Requirement IDs differ from the compiled contract")
    tests = {}
    checks = {}
    if not problems:
        tach = BIN / ("tach.exe" if os.name == "nt" else "tach")
        with tempfile.TemporaryDirectory() as tmp:
            report = Path(tmp) / "pytest.xml"
            for name, cmd in [("tach", [tach, "check"]),
                              ("pytest", [sys.executable, "-m", "pytest", "-q", "--junitxml", report])]:
                result = run(*cmd, cwd=attempt, check=False)
                checks[name] = {"exit": result.returncode, "output": (result.stdout + result.stderr)[-3000:]}
                if result.returncode:
                    problems.append(f"{name} failed")
            if report.exists():
                for case in ElementTree.parse(report).iter("testcase"):
                    key = case.get("classname").replace(".", "/") + ".py::" + case.get("name")
                    tests[key] = not any(case.find(x) is not None for x in ("error", "skipped", "failure"))
            for req, nodes in links.items():
                if not nodes or not all(n.startswith(task.acceptance_file + "::") and tests.get(n) for n in nodes):
                    problems.append(f"{req} lacks passing linked acceptance tests")
    if clean_revision(attempt) != revision:
        problems.append("Revision changed during checks")
    return dict(contract=contract, revision=revision, base=task.revision, intent=task.ticket.intent,
                requirements=task.ticket.requirements, links=links, changed=paths, checks=checks,
                tests=tests, problems=problems, passed=not problems)


def cli():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="op", required=True)
    for name, args in {"route":["paths"], "recheck":["base"], "schema":[], "catalog":[],
                       "context":["query"], "compile":["ticket"], "verify":["contract","attempt","receipt"]}.items():
        p = sub.add_parser(name)
        for arg in args:
            p.add_argument(arg, nargs="+" if arg == "paths" else None)
    args = parser.parse_args()
    if args.op in ("route", "recheck"):
        paths = args.paths if args.op == "route" else diff_paths(args.base)
        result = RuleProvider().decide(paths, ["FAST","STANDARD","FULL"])
    elif args.op == "catalog":
        result = catalog().model_dump()
    elif args.op == "schema":
        result = {m.__name__: m.model_json_schema() for m in (Ticket, Catalog, Task, Receipt)}
    elif args.op == "context":
        result = get_context(args.query)
    elif args.op == "compile":
        result = compile_ticket(Ticket.model_validate_json(Path(args.ticket).read_bytes()))
    else:
        result = verify(args.contract, args.attempt, Receipt.model_validate_json(Path(args.receipt).read_bytes()))
    print(json.dumps(result, indent=2))
    return int(result.get("passed") is False) if isinstance(result, dict) else 0


if __name__ == "__main__":
    try:
        sys.exit(cli())
    except (ValueError, OSError, subprocess.TimeoutExpired) as exc:
        sys.exit(str(exc))
