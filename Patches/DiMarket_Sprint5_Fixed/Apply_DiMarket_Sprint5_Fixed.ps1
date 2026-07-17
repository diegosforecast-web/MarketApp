$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$pythonScript = Join-Path $scriptDir "apply_sprint5.py"

if (-not (Test-Path $pythonScript)) {
    throw "Missing apply_sprint5.py beside this wrapper."
}

python $pythonScript

if ($LASTEXITCODE -ne 0) {
    throw "Sprint 5 installer failed. No successful completion was reported."
}
