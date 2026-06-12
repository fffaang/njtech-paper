param(
    [switch]$DryRun,
    [switch]$SkipInstall,
    [switch]$SkipCheck,
    [switch]$ChinaMirror,
    [string]$Proxy,
    [int]$TimeoutSeconds,
    [string]$Log,
    [switch]$WarmupBrowser
)

$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8

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
if ($ChinaMirror) {
    $argsList += "--china-mirror"
}
if ($Proxy) {
    $argsList += "--proxy"
    $argsList += $Proxy
}
if ($TimeoutSeconds -gt 0) {
    $argsList += "--timeout"
    $argsList += [string]$TimeoutSeconds
}
if ($Log) {
    $argsList += "--log"
    $argsList += $Log
}
if ($WarmupBrowser) {
    $argsList += "--warmup-browser"
}

if ($DryRun) {
    Write-Host "[dry-run] wrapper command: $($python.Source) $($argsList -join ' ')"
}

& $python.Source @argsList
exit $LASTEXITCODE
