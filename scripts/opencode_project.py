"""Launch the user's native OpenCode v2 installation or the checkout's MCP server."""
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys


def _client():
    override = os.environ.get("HARNESS_OPENCODE")
    if override:
        binary = Path(override)
    else:
        # npm activation in this repo also exposes a different, v1 bridge.
        candidates = [Path(p) for p in os.get_exec_path() if p and
                      Path(p).parts[-2:] != ("node_modules", ".bin")]
        match = shutil.which("opencode", path=os.pathsep.join(map(str, candidates)))
        if not match:
            raise ValueError("Install native OpenCode v2 or set HARNESS_OPENCODE")
        binary = Path(match)
        if binary.suffix.lower() == ".cmd":
            binary = binary.parent / "node_modules/@opencode/cli/bin/opencode.exe"
    if not binary.is_absolute() or not binary.is_file() or binary.suffix.lower() in {".bat",".cmd"}:
        raise ValueError("HARNESS_OPENCODE must point to the installed native executable")
    version = subprocess.check_output([binary, "--version"], text=True).strip()
    if not re.fullmatch(r"(?:opencode )?v?2\.[\w.-]+", version):
        raise ValueError("Expected native OpenCode v2, found " + version)
    return binary


def _model(role):
    config = json.loads((Path(__file__).resolve().parents[1] / "opencode.json").read_bytes())
    model = config["agents"]["harness-" + role]["model"]
    if not re.fullmatch(r"opencode-go/[\w.-]+", model):
        raise ValueError("Expected an OpenCode Go model")
    return model


def _reply(output):
    sessions, parts, usage = set(), [], []
    finished = False
    opened = False
    for line in output.splitlines():
        event = json.loads(line)
        if event["type"] == "error":
            raise ValueError("OpenCode returned a model error: " + str(event.get("error", ""))[:600])
        session = event.get("sessionID", "")
        if not re.fullmatch(r"ses_[a-zA-Z0-9]+", session):
            raise ValueError("Invalid OpenCode session ID")
        sessions.add(session)
        part = event["part"]
        if event["type"] == "step_start":
            if opened or finished:
                raise ValueError("Unexpected OpenCode step start")
            opened = True
            parts.clear()
        elif not opened:
            raise ValueError("OpenCode event outside active step")
        elif event["type"] == "text":
            parts.append(part["text"])
        elif event["type"] == "step_finish":
            opened = False
            finished = part["reason"] == "stop"
            usage.append(part["tokens"])
    answer = "".join(parts).strip()
    if len(sessions) != 1 or not finished or not answer:
        raise ValueError("Incomplete OpenCode response or multiple sessions")
    return sessions.pop(), answer, usage


def _balanced_objects(text):
    """Yield every balanced top-level JSON object embedded in a reply."""
    start = None
    depth = 0
    in_string = False
    escaped = False
    for index, char in enumerate(text):
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue
        if char == '"':
            in_string = True
        elif char == "{":
            if depth == 0:
                start = index
            depth += 1
        elif char == "}":
            if depth:
                depth -= 1
                if depth == 0:
                    try:
                        yield json.loads(text[start:index + 1])
                    except ValueError:
                        pass
                    start = None


def _schema_answer(answer, specification):
    """Normalize a structured reply. Some models wrap the required JSON in
    prose or fences: direct JSON passes through unchanged, otherwise exactly
    one unique schema-valid embedded object is accepted. Anything absent or
    ambiguous fails closed rather than guessing."""
    try:
        json.loads(answer)
        return answer
    except ValueError:
        pass
    from jsonschema import ValidationError, validate
    matches = {}
    for candidate in _balanced_objects(answer):
        try:
            validate(candidate, specification)
        except ValidationError:
            continue
        matches[json.dumps(candidate, sort_keys=True)] = candidate
    if len(matches) == 1:
        return json.dumps(next(iter(matches.values())))
    raise ValueError(
        f"OpenCode reply carried {len(matches)} schema-valid JSON objects, expected one")


def _environment():
    return {**os.environ, "HARNESS_CLIENT":"opencode",
            "PATH":str(Path(sys.executable).parent) + os.pathsep + os.environ.get("PATH", "")}


def _run(role, model, prompt, cwd, schema):
    specification = None
    if schema:
        specification = json.loads(schema.read_bytes())
        prompt += "\nReturn only JSON matching this schema:\n" + json.dumps(specification)
    command = [_client(), "run", "--standalone", "--archived", "--agent", "harness-" + role,
               "--model", model, "--format", "json"]
    result = subprocess.run(command, input=prompt, cwd=cwd, env=_environment(), capture_output=True,
                            encoding="utf-8", errors="replace", timeout=1800)
    if result.returncode:
        raise ValueError(f"OpenCode exit {result.returncode}: {result.stderr[-1000:]}")
    thread, answer, usage = _reply(result.stdout)
    if specification is not None:
        answer = _schema_answer(answer, specification)
    return thread, answer, usage


def _server_command():
    root = Path(subprocess.check_output(["git","rev-parse","--show-toplevel"], text=True).strip())
    common = Path(subprocess.check_output(
        ["git","rev-parse","--path-format=absolute","--git-common-dir"], text=True).strip())
    python = common.parent / (".venv/Scripts/python.exe" if os.name == "nt" else ".venv/bin/python")
    return [python, root / "server.py"]


if __name__ == "__main__":
    if sys.argv[1:] == ["--serve-mcp"]:
        sys.exit(subprocess.call(_server_command()))
    sys.exit(subprocess.call([_client(), "--standalone", *sys.argv[1:]],
                             env=_environment()))
