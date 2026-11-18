import json
import subprocess
import uuid
from pathlib import Path

import pytest
import harness as h
from scripts import codex_role as roles


def test_role_commands(tmp_path):
    for role, expected in [("engineer","gpt-6.2-sol"),("architect","gpt-6.2-astra"),("reviewer","gpt-6.2-astra")]:
        args = roles._command(role, False, tmp_path, None)
        assert args[args.index("--model")+1] == expected
        assert "exec" in args and "--ephemeral" in args and "resume" not in args
        assert args[-1] == "-" and args[args.index("--sandbox")+1] == "read-only"


def test_audit_and_reuse(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    h.git("init", "-q")
    h.git("-c","user.name=Test","-c","user.email=test@localhost","commit","--allow-empty","-qm","base")
    thread = str(uuid.uuid4())
    original = subprocess.run
    def fake(args, **kwargs):
        if args[0] == "git":
            return original(args, **kwargs)
        out = Path(args[args.index("--output-last-message")+1])
        out.write_text("OK")
        return subprocess.CompletedProcess(args, 0, json.dumps({"type":"thread.started","thread_id":thread}), "")
    monkeypatch.setattr(subprocess, "run", fake)
    answer, metadata = roles.invoke("engineer", "TASK-A", "inspect")
    assert answer == "OK" and metadata["thread_id"] == thread
    assert json.loads(Path(metadata["receipt"]).read_text())["requested_model"] == "gpt-6.2-sol"
    with pytest.raises(FileExistsError):
        roles.invoke("engineer", "TASK-B", "inspect something else")
    with pytest.raises(ValueError, match="linked worktree"):
        roles.invoke("engineer", "TASK-C", "edit", write=True)
    records = [json.loads(p.read_text()) for p in Path(".harness/roles").glob("*/receipt.json")]
    assert sorted(r["outcome"] for r in records) == ["completed", "failed"]


def test_shared_entry():
    from scripts import live_fixture
    assert live_fixture.invoke is roles.invoke
