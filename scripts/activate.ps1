$root = Split-Path $PSScriptRoot
$env:Path = "$root\.venv\Scripts;$root\node_modules\.bin;$root\scripts;$env:Path"
$env:PYTHONUTF8 = "1"
$env:SIGIL_WORKSPACE = "$root"
