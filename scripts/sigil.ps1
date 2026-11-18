$root = Split-Path $PSScriptRoot
$cwd = (Get-Location).ProviderPath

function Map-SigilPath([string]$path) {
    $full = [IO.Path]::GetFullPath((Join-Path $cwd $path))
    if ($full -ieq $root) { return "/host" }
    if ($full.StartsWith($root + "\", [StringComparison]::OrdinalIgnoreCase)) {
        return "/host/" + $full.Substring($root.Length + 1).Replace("\", "/")
    }
    return $null
}

$forwarded = @(
    foreach ($argument in $args) {
        $text = [string]$argument
        if ($text -match '[\\/]' -and $text -notmatch '^[a-z]+://' -and (Test-Path -LiteralPath $text)) {
            Map-SigilPath $text
        } else {
            $text
        }
    }
)

$inside = Map-SigilPath "."
if (-not $inside) {
    Write-Error "Run sigil from the project root: $root"
    exit 1
}

docker exec -i -w $inside -e "SIGIL_PWD=$inside" sigil /usr/local/bin/sigil @forwarded
exit $LASTEXITCODE
