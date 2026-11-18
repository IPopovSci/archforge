"""Launch one task in a fresh, fixed-role native client session and retain its receipt."""
import argparse
from importlib import metadata as _packages
import json
import os
import re
import subprocess
import sys
import tempfile
import time
import tomllib
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import harness as h
from scripts import opencode_project as _opencode

_MODELS = {"architect": "gpt-6.2-astra", "engineer": "gpt-6.2-sol", "reviewer": "gpt-6.2-astra"}


def _command(role, write, folder, schema):
    command = [sys.executable, str(Path(__file__).with_name("codex_project.py")), "exec",
               "--ephemeral", "--json", "--model", _MODELS[role], "-c", 'model_provider="openai"',
               "--disable", "memories", "--disable", "multi_agent", "--disable", "multi_agent_v2",
               "--sandbox", "workspace-write" if write else "read-only",
               "--output-last-message", str(folder / "answer.txt")]
    if schema:
        command.extend(["--output-schema", str(schema)])
    return [*command, "-"]


def _adapter(client):
    if client == "opencode":
        return _opencode._model, _opencode._run
    matches = list(_packages.entry_points(group="architecture_harness.clients", name=client))
    if len(matches) != 1:
        raise ValueError(f"Expected one installed native adapter for {client!r}")
    adapter = matches[0].load()
    return adapter.model, adapter.run


def _write_result(base, cwd):
    paths = h.diff_paths(base, cwd)
    if not paths:
        raise ValueError("Codex returned without changing the worktree; inspect answer.txt")
    return paths


def invoke(role, task, prompt, *, worktree=None, write=False, schema=None):
    if role not in _MODELS or not task.strip() or not prompt.strip():
        raise ValueError("Expected a named role, task ID and nonempty prompt")
    client = os.environ.get("HARNESS_CLIENT", "codex")
    if not re.fullmatch(r"[a-z][a-z0-9_-]{0,63}", client):
        raise ValueError("Invalid native client name")
    if client != "codex" and write:
        raise ValueError(f"{client} engineering writes require --edit-file")
    adapter = None if client == "codex" else _adapter(client)
    model = adapter[0](role) if adapter else _MODELS[role]
    root = Path(h.git("rev-parse", "--show-toplevel")).resolve()
    common = Path(h.git("rev-parse", "--path-format=absolute", "--git-common-dir")).resolve()
    cwd = Path(worktree or root).resolve()
    actual = Path(h.git("rev-parse", "--path-format=absolute", "--git-common-dir", cwd=cwd)).resolve()
    if actual != common or cwd != Path(h.git("rev-parse", "--show-toplevel", cwd=cwd)).resolve():
        raise ValueError("Expected a checkout root in this Git repository")
    if write:
        if role != "engineer" or cwd == common.parent or not (cwd / ".git").is_file():
            raise ValueError("Writes require the engineer role and a separate linked worktree")
        h.clean_revision(cwd)
    runs = common.parent / ".harness/roles"
    folder = runs / uuid.uuid4().hex
    folder.mkdir(parents=True)
    started = time.monotonic()
    metadata = dict(task=task, role=role, client=client, requested_model=model, cwd=str(cwd),
                    base=h.git("rev-parse","HEAD",cwd=cwd), write=write, thread_id=None,
                    usage=[], outcome="failed", receipt=str(folder / "receipt.json"))
    try:
        schema = Path(schema).resolve() if schema else None
        instruction = f"You are the assigned {role} for task {task}. Complete this task directly.\n"
        if adapter:
            thread, answer, metadata["usage"] = adapter[1](role, model, instruction+prompt, cwd, schema)
            if not isinstance(thread, str) or not re.fullmatch(r"[a-zA-Z0-9_-]{1,160}", thread):
                raise ValueError("Invalid native session ID")
            (folder / "answer.txt").write_text(answer, encoding="utf-8")
        else:
            result = subprocess.run(_command(role, write, folder, schema), cwd=cwd, input=instruction+prompt,
                                    capture_output=True, encoding="utf-8", errors="replace", timeout=1800)
            ids = []
            for line in result.stdout.splitlines():
                try:
                    event = json.loads(line)
                except ValueError:
                    continue
                if event.get("type") == "thread.started":
                    ids.append(str(uuid.UUID(event["thread_id"])))
                if event.get("usage"):
                    metadata["usage"].append(event["usage"])
            if result.returncode or len(ids) != 1:
                raise ValueError(f"Codex exit {result.returncode}, observed {len(ids)} thread starts. "
                                 + (result.stderr + result.stdout)[-1200:])
            thread = ids[0]
        metadata["thread_id"] = thread
        threads = runs / "threads"
        threads.mkdir(exist_ok=True)
        marker_name = f"{client}.{thread}" if adapter else thread
        with (threads / marker_name).open("x", encoding="utf-8") as marker:
            marker.write(folder.name)
        answer = (folder / "answer.txt").read_text(encoding="utf-8").strip()
        if not answer:
            raise ValueError(f"{client} returned an empty response")
        if schema:
            from jsonschema import validate
            validate(json.loads(answer), json.loads(schema.read_bytes()))
        if write:
            metadata["changed"] = _write_result(metadata["base"], cwd)
        metadata["outcome"] = "completed"
        return answer, metadata
    except Exception as exc:
        metadata["error"] = str(exc)
        raise
    finally:
        metadata["seconds"] = round(time.monotonic()-started, 2)
        Path(metadata["receipt"]).write_text(json.dumps(metadata, indent=2), encoding="utf-8")


def _validate_edit(before, after):
    if before == after:
        raise ValueError("Engineer returned unchanged source")
    if h.public_api_digest(before) != h.public_api_digest(after):
        raise ValueError("Proposed public interface change requires FULL review")


def _edit_file(task, prompt, worktree, relative):
    cwd = worktree.resolve()
    common = Path(h.git("rev-parse", "--path-format=absolute", "--git-common-dir")).resolve()
    if cwd == common.parent or not (cwd / ".git").is_file() or Path(h.git(
            "rev-parse", "--path-format=absolute", "--git-common-dir", cwd=cwd)).resolve() != common:
        raise ValueError("Expected a separate linked checkout of this repository")
    base = h.clean_revision(cwd)
    policy = tomllib.loads((cwd / "tach.toml").read_text(encoding="utf-8"))
    owned = {m["path"].replace(".", "/") + ".py" for m in policy["modules"]}
    target = cwd / relative
    if relative not in owned or target.resolve() != target or not target.is_file():
        raise ValueError("Expected one existing policy-owned source file")
    h.git("ls-files", "--error-unmatch", "--", relative, cwd=cwd)
    before = target.read_text(encoding="utf-8")
    request = json.dumps({"request":prompt, "file":relative, "current_source":before})
    with tempfile.TemporaryDirectory() as tmp:
        schema = Path(tmp) / "edit.json"
        schema.write_text(json.dumps({"type":"object","properties":{"source":{"type":"string"}},
                                      "required":["source"],"additionalProperties":False}))
        answer, metadata = invoke("engineer",task,
            "Use only the supplied source. Return the complete edited source. Keep its public API. " + request,
            worktree=cwd,schema=schema)
    record = dict(task=task, base=base, file=relative, thread_id=metadata["thread_id"], passed=False, checks={})
    try:
        after = json.loads(answer)["source"]
        _validate_edit(before, after)
        if h.clean_revision(cwd) != base or target.read_text(encoding="utf-8") != before:
            raise ValueError("Candidate changed during inference")
        with tempfile.NamedTemporaryFile(dir=target.parent,delete=False) as staging:
            staged = Path(staging.name)
        try:
            staged.write_text(after, encoding="utf-8")
            os.replace(staged, target)
        finally:
            staged.unlink(missing_ok=True)
        for name, command in [("tach",[h.BIN/"tach","check"]),("pytest",[sys.executable,"-m","pytest","-q"])]:
            outcome = h.run(*command,cwd=cwd,check=False)
            record["checks"][name] = {"exit":outcome.returncode,"output":(outcome.stdout+outcome.stderr)[-2000:]}
        record["changed"] = h.diff_paths(base,cwd)
        if record["changed"] != [relative] or any(c["exit"] for c in record["checks"].values()):
            raise ValueError("Verification failed; see edit.json")
        record["passed"] = True
        return record
    finally:
        Path(metadata["receipt"]).with_name("edit.json").write_text(json.dumps(record,indent=2),encoding="utf-8")


def _main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("role", choices=list(_MODELS))
    parser.add_argument("task")
    parser.add_argument("--client", help="Native client name, defaults to HARNESS_CLIENT or codex")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--prompt")
    group.add_argument("--prompt-file", type=Path)
    parser.add_argument("--worktree", type=Path)
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--edit-file", help="Apply one explicitly scoped, verified STANDARD edit")
    args = parser.parse_args()
    if args.client:
        os.environ["HARNESS_CLIENT"] = args.client
    prompt = args.prompt if args.prompt_file is None else args.prompt_file.read_text(encoding="utf-8")
    if args.edit_file:
        if args.role != "engineer" or not args.worktree or args.write:
            parser.error("--edit-file requires engineer and --worktree; use it without --write")
        print(json.dumps(_edit_file(args.task,prompt,args.worktree,args.edit_file),indent=2))
        return
    answer, record = invoke(args.role,args.task,prompt,worktree=args.worktree,write=args.write)
    print(answer)
    print("Receipt:", record["receipt"], file=sys.stderr)


if __name__ == "__main__":
    _main()
