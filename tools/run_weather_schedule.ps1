param(
    [ValidateRange(1, 24)][int]$Runs = 1,
    [ValidateRange(0, 3600)][int]$IntervalSeconds = 60,
    [ValidateRange(1, 900)][int]$TimeoutSeconds = 300,
    [ValidateRange(1, 3600)][int]$MaxSeconds = 900
)

$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$pythonPath = Join-Path $projectRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $pythonPath -PathType Leaf)) {
    throw 'Create the project virtual environment before running the weather schedule.'
}
$scheduleExitCode = 2
Push-Location -LiteralPath $projectRoot
try {
    & $pythonPath -m ingestion schedule --plan config/weather-release-plan.json `
        --runs $Runs --interval-seconds $IntervalSeconds `
        --timeout-seconds $TimeoutSeconds --max-seconds $MaxSeconds
    $scheduleExitCode = $LASTEXITCODE
}
finally {
    Pop-Location
}
exit $scheduleExitCode
