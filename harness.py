"""Host-neutral compiler and verification commands. Run from the target repository root."""
import argparse
import ast
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
    checks: list[str] = Field(default_factory=list)


class Catalog(Record):
    revision: str
    modules: dict[str, str]


class ReviewedDelta(Record):
    """Reviewer-supplied input in the trusted checkout (CLI only)."""
    revision: str
    ticket_digest: str
    rationale: str = Field(min_length=1)
    extra_paths: list[str]
    public_api: dict[str, str]
    file_digests: dict[str, str] = Field(default_factory=dict)


class Task(Record):
    ticket: Ticket
    revision: str
    scope: list[str]
    acceptance_file: str
    checks: list[str]
    evidence: list[dict]
    review: ReviewedDelta | None = None


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
    entry = Path("node_modules/@trailhq/trail-code/dist/bin/trail.js")
    location = INSTALL / entry
    if not location.exists():
        common = git("rev-parse", "--path-format=absolute", "--git-common-dir", cwd=INSTALL)
        location = Path(common).parent / entry
    return run(binary, location, *args).stdout


def catalog():
    revision = clean_revision()
    policy = tomllib.loads(Path("tach.toml").read_text())
    modules = {row["path"]: row["path"].replace(".", "/") + ".py" for row in policy["modules"]}
    tracked = git("ls-files", "-z", "--", "*.py").rstrip("\0").split("\0")
    roots = sorted({p.split("/")[0] for p in [*modules.values(), *tracked] if p} | {"tests"})
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


def _context(query, cat):
    if not query.strip() or len(query) > 1000 or query.startswith("-"):
        raise ValueError("Provide a short search phrase.")
    hits = json.loads(trail("ask", query, ".", "--json", "--source", "-n", "6"))["hits"]
    return [dict(pointer=h["pointer"], title=h["title"][:120], code=h.get("code", "")[:650],
                 revision=cat.revision, reason="Trail query match") for h in hits if h.get("pointer")]


def get_context(query):
    return _context(query, catalog())


def ticket_digest(ticket):
    return hashlib.sha256(json.dumps(ticket.model_dump(), sort_keys=True).encode()).hexdigest()


def _validate_review(review, ticket, revision, scope):
    if review.revision != revision or review.ticket_digest != ticket_digest(ticket):
        raise ValueError("Review belongs to a different revision or ticket")
    for path in review.extra_paths:
        if not re.fullmatch(r"[A-Za-z0-9_][A-Za-z0-9_./-]*", path) or any(
            part in ("", ".", "..", "node_modules", "__pycache__") or part.startswith(".")
            for part in path.split("/")
        ):
            raise ValueError(f"Invalid repository path: {path}")
    if not (set(review.public_api) | set(review.file_digests)) <= (scope | set(review.extra_paths)):
        raise ValueError("Reviewed interface outside approved files")
    protected = {p for p in review.extra_paths if not p.endswith(".py") or p.startswith("tests/")}
    if not protected <= review.file_digests.keys():
        raise ValueError("Policy, configuration and test changes require reviewed file digests")
    if any(not re.fullmatch("[a-f0-9]{64}", digest) for digest in
           [*review.public_api.values(), *review.file_digests.values()]):
        raise ValueError("Expected SHA-256 of approved interface")


STRUCTURAL_CHECKS = ("requirement links", "scope")
DEFAULT_CHECKS = ("tach", "pytest", "requirement links", "scope", "doc_gates")


def check_commands(report):
    """Named subprocess checks a compiled contract can request, run in the
    candidate worktree. A check is any command that exits nonzero on
    violation, so adapters stay pluggable rows rather than core structure:
    the Python gates and the documentation gate are this repository's
    defaults, and language-specific gates are registered rows that a
    project's tickets declare, such as the Godot boundary adapter under
    the root godot.toml convention."""
    tach = BIN / ("tach.exe" if os.name == "nt" else "tach")
    return {
        "tach": [str(tach), "check"],
        "pytest": [sys.executable, "-m", "pytest", "-q", "--junitxml", str(report)],
        "doc_gates": [sys.executable, "scripts/doc_catalog.py", "check", "."],
        "godot_boundaries": [sys.executable, "scripts/godot_boundaries.py", ".", "--policy", "godot.toml"],
    }


def compile_ticket(ticket, review=None):
    """Compile a revision-bound contract. The check list is frozen at compile
    time: a ticket that changes the compiler itself is therefore verified
    against the pre-change list, and the next compiled contract exercises
    the change. Acceptance tests carry the proof across that boundary."""
    structural = set(ticket.checks) & set(STRUCTURAL_CHECKS)
    if structural:
        raise ValueError(f"Structural checks are not ticket-declarable: {sorted(structural)}")
    commands = check_commands(Path("pytest.xml"))
    unknown = set(ticket.checks) - commands.keys()
    if unknown:
        raise ValueError(f"Unknown check names: {sorted(unknown)}")
    cat = catalog()
    modules = dict(cat.modules)
    if review:
        for component in set(ticket.components) - modules.keys():
            path = component.replace(".", "/") + ".py"
            if path in review.extra_paths and "tach.toml" in review.extra_paths and not Path(path).exists():
                modules[component] = path
    if ticket.unknowns or set(ticket.components) - modules.keys():
        raise ValueError("Resolve unknowns and component references before compilation.")
    acceptance = "tests/test_" + ticket.id.lower().replace("-", "_") + ".py"
    if Path(acceptance).exists():
        raise ValueError("Ticket needs a fresh acceptance test file.")
    scope = {modules[c] for c in ticket.components} | {acceptance}
    if review:
        _validate_review(review, ticket, cat.revision, scope)
        scope.update(review.extra_paths)
    task = Task(version=1, ticket=ticket, revision=cat.revision,
                scope=sorted(scope), review=review,
                acceptance_file=acceptance,
                checks=list(dict.fromkeys((*DEFAULT_CHECKS, *ticket.checks))),
                evidence=_context(ticket.intent, cat))
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
    components = {p for p in paths if not p.startswith("tests/")}
    policy = tomllib.loads(Path("tach.toml").read_text())
    owned = {m["path"].replace(".", "/") + ".py" for m in policy["modules"]}
    if len(components) <= 1 and components <= owned and all(p.endswith(".py") for p in paths):
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


def public_api_digest(source):
    """Fingerprint public Python definitions, class fields and callable signatures."""
    def surface(body):
        entries = []
        for node in body:
            name = getattr(node, "name", "")
            if name.startswith("_") and name != "__init__":
                continue
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                node.body = [ast.Pass()]
                entries.append(ast.dump(node))
            elif isinstance(node, ast.ClassDef):
                members = surface(node.body)
                node.body = [ast.Pass()]
                entries.append((ast.dump(node), members))
            elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
                if not node.target.id.startswith("_"):
                    entries.append(ast.dump(node))
            elif isinstance(node, ast.Assign):
                names = sorted({part.id for target in node.targets for part in ast.walk(target)
                                if isinstance(part, ast.Name) and isinstance(part.ctx, ast.Store)
                                and not part.id.startswith("_")})
                if names:
                    entries.append(("bindings", names))
                if any(isinstance(t, ast.Name) and t.id == "__all__" for t in node.targets):
                    entries.append(ast.dump(node))
        return entries
    return hashlib.sha256(json.dumps(surface(ast.parse(source).body)).encode()).hexdigest()


def _api_changes(task, revision, paths, attempt):
    problems = []
    for path in paths:
        if not path.endswith(".py") or path.startswith("tests/"):
            continue
        sources = []
        for ref in (task.revision, revision):
            blob = run("git", "show", f"{ref}:{path}", cwd=attempt, check=False)
            sources.append(blob.stdout if blob.returncode == 0 else "")
        try:
            before, after = map(public_api_digest, sources)
        except SyntaxError as exc:
            problems.append(f"Invalid Python in {path}: {exc}")
            continue
        if before != after and (task.review is None or task.review.public_api.get(path) != after):
            problems.append(f"Unapproved public interface change in {path}: {after}")
    return problems


def recheck(base):
    paths = diff_paths(base)
    result = RuleProvider().decide(paths, ["FAST", "STANDARD", "FULL"])
    if result["choice"] == "STANDARD":
        for path in paths:
            if path.startswith("tests/"):
                continue
            before = run("git", "show", f"{base}:{path}", check=False)
            try:
                after = Path(path).read_text(encoding="utf-8") if Path(path).exists() else ""
                changed = public_api_digest(before.stdout) != public_api_digest(after)
            except (SyntaxError, UnicodeError):
                changed = True
            if changed:
                result.update(choice="FULL", scores={"FULL": 1}, reason=f"Public interface changed: {path}")
                break
    return result


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
    if not problems:
        problems.extend(_api_changes(task, revision, paths, attempt))
        for path, digest in (task.review.file_digests.items() if task.review else ()):
            candidate = Path(attempt) / path
            if not candidate.is_file() or hashlib.sha256(candidate.read_bytes()).hexdigest() != digest:
                problems.append(f"File differs from reviewed content: {path}")
        if task.review and "tach.toml" in task.review.extra_paths:
            try:
                policy = tomllib.loads((Path(attempt) / "tach.toml").read_text(encoding="utf-8"))
                declared = {m["path"] for m in policy["modules"]}
                present = {name for name in declared if
                           (Path(attempt) / (name.replace(".", "/") + ".py")).is_file()}
                missing = set(task.ticket.components) - present
                if missing:
                    problems.append(f"Candidate policy omits required components: {sorted(missing)}")
            except (OSError, ValueError, KeyError, TypeError) as exc:
                problems.append(f"Invalid candidate policy: {exc}")
    links = receipt.requirement_test_links
    if set(links) != set(task.ticket.requirements):
        problems.append("Requirement IDs differ from the compiled contract")
    tests = {}
    checks = {}
    if not problems:
        with tempfile.TemporaryDirectory() as tmp:
            report = Path(tmp) / "pytest.xml"
            commands = check_commands(report)
            for name in task.checks:
                if name in STRUCTURAL_CHECKS:
                    continue
                if name not in commands:
                    problems.append(f"Unknown contract check: {name}")
                    continue
                result = run(*commands[name], cwd=attempt, check=False)
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
                       "context":["query"], "compile":["ticket"], "ticket-digest":["ticket"],
                       "api-digest":["source"], "verify":["contract","attempt","receipt"]}.items():
        p = sub.add_parser(name)
        if name == "compile":
            p.add_argument("--review", help="Reviewer-owned, revision-bound architecture delta JSON")
        for arg in args:
            p.add_argument(arg, nargs="+" if arg == "paths" else None)
    args = parser.parse_args()
    if args.op == "route":
        result = RuleProvider().decide(args.paths, ["FAST","STANDARD","FULL"])
    elif args.op == "recheck":
        result = recheck(args.base)
    elif args.op == "catalog":
        result = catalog().model_dump()
    elif args.op == "schema":
        result = {m.__name__: m.model_json_schema() for m in (Ticket, Catalog, ReviewedDelta, Task, Receipt)}
    elif args.op == "context":
        result = get_context(args.query)
    elif args.op in ("compile", "ticket-digest"):
        ticket = Ticket.model_validate_json(Path(args.ticket).read_bytes())
        if args.op == "ticket-digest":
            result = ticket_digest(ticket)
        else:
            review = ReviewedDelta.model_validate_json(Path(args.review).read_bytes()) if args.review else None
            result = compile_ticket(ticket, review)
    elif args.op == "api-digest":
        result = public_api_digest(Path(args.source).read_text(encoding="utf-8"))
    else:
        result = verify(args.contract, args.attempt, Receipt.model_validate_json(Path(args.receipt).read_bytes()))
    print(json.dumps(result, indent=2))
    return int(result.get("passed") is False) if isinstance(result, dict) else 0


if __name__ == "__main__":
    try:
        sys.exit(cli())
    except (ValueError, OSError, subprocess.TimeoutExpired) as exc:
        sys.exit(str(exc))
