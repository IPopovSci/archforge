"""Launch one task in a fresh, fixed-role Codex session and retain its receipt."""
import argparse
import json
import subprocess
import sys
import time
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import harness as h

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


def invoke(role, task, prompt, *, worktree=None, write=False, schema=None):
    if role not in _MODELS or not task.strip() or not prompt.strip():
        raise ValueError("Expected a named role, task ID and nonempty prompt")
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
    metadata = dict(task=task, role=role, requested_model=_MODELS[role], cwd=str(cwd),
                    base=h.git("rev-parse","HEAD",cwd=cwd), write=write, thread_id=None,
                    usage=[], outcome="failed", receipt=str(folder / "receipt.json"))
    try:
        schema = Path(schema).resolve() if schema else None
        instruction = f"You are the assigned {role} for task {task}. Complete this task directly.\n"
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
        metadata["thread_id"] = ids[0]
        threads = runs / "threads"
        threads.mkdir(exist_ok=True)
        with (threads / ids[0]).open("x", encoding="utf-8") as marker:
            marker.write(folder.name)
        answer = (folder / "answer.txt").read_text(encoding="utf-8").strip()
        if not answer:
            raise ValueError("Codex returned an empty response")
        metadata["outcome"] = "completed"
        return answer, metadata
    except Exception as exc:
        metadata["error"] = str(exc)
        raise
    finally:
        metadata["seconds"] = round(time.monotonic()-started, 2)
        Path(metadata["receipt"]).write_text(json.dumps(metadata, indent=2), encoding="utf-8")


def _main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("role", choices=list(_MODELS))
    parser.add_argument("task")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--prompt")
    group.add_argument("--prompt-file", type=Path)
    parser.add_argument("--worktree", type=Path)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    prompt = args.prompt if args.prompt_file is None else args.prompt_file.read_text(encoding="utf-8")
    answer, record = invoke(args.role,args.task,prompt,worktree=args.worktree,write=args.write)
    print(answer)
    print("Receipt:", record["receipt"], file=sys.stderr)


if __name__ == "__main__":
    _main()
