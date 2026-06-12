param(
    [switch]$DryRun,
    [switch]$SkipInstall,
    [switch]$SkipCheck
)

$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$bootstrap = Join-Path $scriptDir "bootstrap_njtech_paper.py"

if (-not (Test-Path -LiteralPath $bootstrap)) {
    throw "bootstrap_njtech_paper.py not found next to this script."
}

$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $python) {
    $python = Get-Command py -ErrorAction SilentlyContinue
}
if (-not $python) {
    throw "Python 3.11+ was not found on PATH."
}

$argsList = @($bootstrap)
if ($DryRun) {
    $argsList += "--dry-run"
}
if ($SkipInstall) {
    $argsList += "--skip-install"
}
if ($SkipCheck) {
    $argsList += "--skip-check"
}

& $python.Source @argsList
exit $LASTEXITCODE
