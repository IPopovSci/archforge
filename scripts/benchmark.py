"""Run paired baseline/context model benchmarks in disposable worktrees."""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import harness as h
from scripts import codex_role as roles


def load_tasks(path="benchmarks/tasks.json"):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    tasks = data.get("tasks", [])
    ids = [task["id"] for task in tasks]
    if not tasks or len(ids) != len(set(ids)):
        raise ValueError("Benchmark tasks require unique nonempty IDs")
    for task in tasks:
        required = {"id", "profile", "request", "file", "context_query", "test_file", "test_source", "test_command"}
        missing = required - task.keys()
        if missing:
            raise ValueError(f"Benchmark task {task.get('id')} is missing fields: {sorted(missing)}")
        if task["profile"] not in {"FAST", "STANDARD", "FULL"}:
            raise ValueError(f"Benchmark task {task['id']} has an invalid profile")
        if not re.fullmatch(r"[a-z0-9-]+", task["id"]):
            raise ValueError(f"Benchmark task {task['id']} has an invalid ID")
    return tasks


def token_totals(usage):
    input_tokens = output_tokens = cached_tokens = 0
    for event in usage:
        input_tokens += int(event.get("input", event.get("input_tokens", 0)) or 0)
        output_tokens += int(event.get("output", event.get("output_tokens", 0)) or 0)
        cached_tokens += int(event.get("cacheRead", event.get("cached_input_tokens", 0)) or 0)
    return {"input": input_tokens, "output": output_tokens, "cached": cached_tokens}


def _source_schema(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({
        "type": "object",
        "properties": {"source": {"type": "string"}},
        "required": ["source"],
        "additionalProperties": False,
    }), encoding="utf-8")
    return path


def _clean_context(worktree, query):
    result = subprocess.run([sys.executable, "harness.py", "context", query], cwd=worktree,
                            capture_output=True, encoding="utf-8", errors="replace", timeout=180)
    if result.returncode:
        raise ValueError((result.stdout + result.stderr)[-2000:])
    return json.loads(result.stdout)


def _apply_seed(worktree, task):
    target = worktree / task["file"]
    if not target.is_file():
        raise ValueError(f"Benchmark target does not exist: {task['file']}")
    source = target.read_text(encoding="utf-8")
    mutation = task.get("mutation")
    if mutation:
        if source.count(mutation["find"]) != 1:
            raise ValueError(f"Benchmark seed for {task['id']} is not unique or missing")
        source = source.replace(mutation["find"], mutation["replace"], 1)
        target.write_text(source, encoding="utf-8")
    test = worktree / task["test_file"]
    test.parent.mkdir(parents=True, exist_ok=True)
    test.write_text(task["test_source"], encoding="utf-8")
    return source


def _prompt(task, source, context):
    payload = {
        "request": task["request"],
        "file": task["file"],
        "current_source": source,
    }
    if context is not None:
        payload["evidence"] = context
    return json.dumps(payload, indent=2)


def _worktree(root, name):
    path = root / ".harness/benchmark/worktrees" / name
    if path.exists():
        shutil.rmtree(path)
    h.git("worktree", "add", "--detach", str(path), "HEAD")
    return path


def _remove_worktree(path):
    h.git("worktree", "remove", "--force", str(path))


def _run_task(task, treatment, root, schema):
    name = f"{task['id']}-{treatment}-{uuid.uuid4().hex[:8]}"
    worktree = _worktree(root, name)
    try:
        context = _clean_context(worktree, task["context_query"]) if treatment == "context" else None
        source = _apply_seed(worktree, task)
        if treatment == "seed":
            metadata = {"client": None, "requested_model": None, "thread_id": None,
                        "seconds": 0.0, "usage": [], "receipt": None}
        else:
            prompt = _prompt(task, source, context)
            answer, metadata = roles.invoke("engineer", f"BENCH-{task['id']}-{treatment}", prompt,
                                              worktree=worktree, schema=schema)
            candidate = json.loads(answer)["source"]
            target = worktree / task["file"]
            target.write_text(candidate, encoding="utf-8")
        command = list(task["test_command"])
        if command and command[0] == "python":
            command[0] = sys.executable
        result = subprocess.run(command, cwd=worktree, capture_output=True, encoding="utf-8",
                                errors="replace", timeout=180)
        changed = h.diff_paths(h.git("rev-parse", "HEAD", cwd=worktree), worktree)
        record = {
            "task": task["id"], "profile": task["profile"], "treatment": treatment,
            "client": metadata.get("client"), "model": metadata.get("requested_model"),
            "thread_id": metadata.get("thread_id"), "passed": result.returncode == 0,
            "seconds": metadata.get("seconds"), "tokens": token_totals(metadata.get("usage", [])),
            "changed_files": changed, "test_exit": result.returncode,
            "test_output": (result.stdout + result.stderr)[-2000:],
            "receipt": metadata.get("receipt"), "worktree": str(worktree),
        }
        return record
    finally:
        _remove_worktree(worktree)


def _summary(results):
    summary = {}
    for treatment in sorted({row["treatment"] for row in results}):
        rows = [row for row in results if row["treatment"] == treatment]
        summary[treatment] = {
            "tasks": len(rows),
            "passed": sum(row["passed"] for row in rows),
            "missed_full": sum(row["profile"] == "FULL" and not row["passed"] for row in rows),
            "seconds": round(sum(row["seconds"] or 0 for row in rows), 2),
            "input_tokens": sum(row["tokens"]["input"] for row in rows),
            "output_tokens": sum(row["tokens"]["output"] for row in rows),
            "cached_tokens": sum(row["tokens"]["cached"] for row in rows),
        }
        for profile in ("FAST", "STANDARD", "FULL"):
            selected = [row for row in rows if row["profile"] == profile]
            summary[treatment][profile] = {
                "total": len(selected), "passed": sum(row["passed"] for row in selected)
            }
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--client", choices=["codex", "opencode"], default="codex")
    parser.add_argument("--tasks", nargs="+", help="Run only these benchmark task IDs")
    parser.add_argument("--treatments", nargs="+", choices=["seed", "baseline", "context"], default=["baseline", "context"])
    parser.add_argument("--dry-run", action="store_true", help="Validate every seeded task without model calls")
    parser.add_argument("--limit", type=int, help="Run only the first N selected tasks")
    args = parser.parse_args()
    os.environ["HARNESS_CLIENT"] = args.client
    tasks = load_tasks()
    if args.dry_run:
        args.treatments = ["seed"]
    if args.tasks:
        selected = {task["id"] for task in tasks}
        unknown = set(args.tasks) - selected
        if unknown:
            parser.error(f"Unknown benchmark tasks: {sorted(unknown)}")
        tasks = [task for task in tasks if task["id"] in set(args.tasks)]
    if args.limit is not None and args.limit >= 0:
        tasks = tasks[:args.limit]
    root = Path(h.git("rev-parse", "--show-toplevel")).resolve()
    output_dir = root / ".harness/benchmark/results"
    output_dir.mkdir(parents=True, exist_ok=True)
    schema = _source_schema(output_dir / "source-schema.json")
    results = []
    for task in tasks:
        for treatment in args.treatments:
            print(f"Running {task['id']} ({treatment})", flush=True)
            results.append(_run_task(task, treatment, root, schema))
    run_id = time.strftime("%Y%m%d-%H%M%S")
    output = output_dir / f"{run_id}.json"
    output.write_text(json.dumps({"client": args.client, "tasks": tasks, "results": results,
                                  "summary": _summary(results)}, indent=2), encoding="utf-8")
    print(json.dumps({"output": str(output), "summary": _summary(results)}, indent=2))
    return 0


if __name__ == "__main__":
    main()
