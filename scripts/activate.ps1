$root = Split-Path $PSScriptRoot
$env:Path = "$root\.venv\Scripts;$root\node_modules\.bin;$env:Path"
$env:PYTHONUTF8 = "1"
