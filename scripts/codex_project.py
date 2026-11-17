"""Launch Codex with this installation's MCP server, including in a Git worktree."""
import json
import subprocess
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[1]
config = {"command": sys.executable, "args": [str(root / "server.py")], "cwd": str(Path.cwd())}
options = []
for key, value in config.items():
    options.extend(["-c", f"mcp_servers.architecture_harness.{key}={json.dumps(value)}"])
sys.exit(subprocess.call(["codex", *options, *sys.argv[1:]]))
