$ErrorActionPreference = "Stop"

$package = Split-Path -Parent $MyInvocation.MyCommand.Path
$backend = "C:\Dev\MarketApp\src\MarketApp\backend"
$frontend = "C:\Dev\MarketApp\frontend"
$stamp = Get-Date -Format "yyyyMMdd_HHmmss"

$targets = @(
  "$backend\services\prediction_history_service.py",
  "$backend\endpoints\history.py",
  "$frontend\src\components\PredictionHistory.jsx"
)

foreach ($target in $targets) {
  if (-not (Test-Path $target)) {
    throw "Required target file was not found: $target"
  }

  Copy-Item $target "$target.$stamp.bak" -Force
}

Copy-Item `
  "$package\backend\services\prediction_history_service.py" `
  "$backend\services\prediction_history_service.py" `
  -Force

Copy-Item `
  "$package\backend\endpoints\history.py" `
  "$backend\endpoints\history.py" `
  -Force

Copy-Item `
  "$package\frontend\src\components\PredictionHistory.jsx" `
  "$frontend\src\components\PredictionHistory.jsx" `
  -Force

Copy-Item `
  "$package\frontend\src\components\Sprint6Transparency.css" `
  "$frontend\src\components\Sprint6Transparency.css" `
  -Force

Write-Host ""
Write-Host "Sprint 6 installed successfully." -ForegroundColor Green
Write-Host "Backups use timestamp: $stamp"
Write-Host "Restart both backend and frontend."
