import asyncio
import json
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest
from jsonschema import ValidationError
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from scripts import codex_role as roles, opencode_project as native


def test_roles(tmp_path):
    for role in ("architect", "engineer", "reviewer"):
        expected = "glm-5.3-flash" if role == "engineer" else "glm-5.3"
        assert native._model(role) == "opencode-go/" + expected
        command = roles._command(role, False, tmp_path, None)
        assert 'model_provider="openai"' in command and "--ephemeral" in command
        model = command[command.index("--model")+1]
        assert model == ("gpt-6.2-sol" if role == "engineer" else "gpt-6.2-astra")


def test_session(monkeypatch, tmp_path):
    def event(kind, **part):
        return json.dumps({"type":kind, "sessionID":"ses_123", "part":part})
    text = event("text", text="42")
    done = event("step_finish", reason="stop", tokens={"output":1})
    stream = "\n".join([event("step_start"), text, done])
    def run(command, **kwargs):
        assert "--session" not in command and "--continue" not in command
        assert "--standalone" in command and "--archived" in command
        assert "JSON" in kwargs["input"]
        return subprocess.CompletedProcess(command, 0, stream, "")
    monkeypatch.setattr(native, "_client", lambda: "native")
    monkeypatch.setattr(subprocess, "run", run)
    schema = tmp_path / "schema.json"
    schema.write_text('{"type":"integer"}')
    assert native._run("engineer", native._model("engineer"), "answer", tmp_path, schema) == (
        "ses_123", "42", [{"output":1}])
    for invalid in [text, text+"\n"+done.replace("ses_123","ses_456"),
                    json.dumps({"type":"error"}), text+"\n"+done.replace("stop","length")]:
        with pytest.raises(ValueError):
            native._reply(invalid)


def test_mcp():
    root = Path.cwd()
    python, server = native._server_command()
    assert server == root / "server.py" and python.is_file()
    config = json.loads((root / "opencode.json").read_bytes())
    assert config["mcp"]["servers"]["architecture_harness"]["command"][-1] == "--serve-mcp"
    async def route():
        params = StdioServerParameters(command=str(python), args=[str(server)], cwd=str(root))
        async with stdio_client(params) as streams, ClientSession(*streams) as session:
            await session.initialize()
            result = await session.call_tool("route_task", {"paths":["README.md"]})
            assert json.loads(result.content[0].text)["choice"] == "FAST"
    asyncio.run(route())


def test_portable(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    subprocess.run(["git","init","-q"], check=True)
    subprocess.run(["git","-c","user.name=Test","-c","user.email=test@localhost","commit",
                    "--allow-empty","-qm","base"], check=True)
    answers = iter([("session1","42",[]), ("session1","42",[]), ("session2","false",[])])
    adapter = SimpleNamespace(model=lambda role: "test/fast", run=lambda *args: next(answers))
    def installed(group, name):
        assert (group, name) == ("architecture_harness.clients", "example")
        return [SimpleNamespace(load=lambda:adapter)]
    monkeypatch.setattr(roles._packages,"entry_points",installed)
    monkeypatch.setenv("HARNESS_CLIENT","example")
    schema = tmp_path / "schema.json"
    schema.write_text('{"type":"integer"}')
    answer, record = roles.invoke("engineer","REQ-1","Inspect",schema=schema)
    assert (answer, record["client"], record["requested_model"]) == ("42","example","test/fast")
    with pytest.raises(FileExistsError):
        roles.invoke("engineer","REQ-2","Inspect",schema=schema)
    with pytest.raises(ValidationError):
        roles.invoke("engineer","REQ-3","Inspect",schema=schema)
