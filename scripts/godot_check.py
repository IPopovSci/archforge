"""Run a headless Godot command as a harness check.

``run_check`` returns the same ``{"exit", "output"}`` shape the verifier
records for Tach and pytest, so a future compiled-check integration can
consume it unchanged. The ``selftest`` convenience composes the canonical
headless run used by game projects:

    python scripts/godot_check.py selftest <project> --godot <binary>

Generic commands run through ``run`` with a timeout; the command's exit code
and output are reported as data and the adapter itself exits 0 once the
command ran:

    python scripts/godot_check.py run --timeout 60 -- godot --headless ...
"""
import argparse
import json
import os
import subprocess
import sys

TAIL = 3000


def run_check(command, cwd=None, timeout=120):
    """Execute one command and report its exit code, captured output and timeouts."""
    try:
        result = subprocess.run(command, cwd=cwd, capture_output=True, encoding="utf-8",
                                errors="replace", timeout=timeout)
    except subprocess.TimeoutExpired:
        return {"exit": 124, "output": f"command timed out after {timeout}s"}
    except OSError as exc:
        return {"exit": 126, "output": f"command failed to start: {exc}"}
    return {"exit": result.returncode, "output": (result.stdout + result.stderr)[-TAIL:]}


def compose_selftest(project, godot=None):
    """Build the headless selftest command for a Godot project."""
    binary = godot or os.environ.get("GODOT_BIN") or "godot"
    return [binary, "--headless", "--path", str(project), "-s", "res://tests/selftest.gd"]


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="op", required=True)
    run_p = sub.add_parser("run")
    run_p.add_argument("--timeout", type=int, default=120)
    run_p.add_argument("--cwd")
    run_p.add_argument("command", nargs=argparse.REMAINDER)
    self_p = sub.add_parser("selftest")
    self_p.add_argument("project")
    self_p.add_argument("--godot")
    self_p.add_argument("--timeout", type=int, default=120)
    self_p.add_argument("--cwd")
    args = parser.parse_args(argv)
    if args.op == "selftest":
        command = compose_selftest(args.project, args.godot)
    else:
        command = list(args.command)
        if command and command[0] == "--":
            command = command[1:]
        if not command:
            parser.error("run requires a command")
    print(json.dumps(run_check(command, cwd=args.cwd, timeout=args.timeout), indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
