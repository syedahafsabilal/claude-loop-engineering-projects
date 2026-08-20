# Project-9 one-off run script (A1 / A3 one-off schedule via shell timer).
# NOT a repeating scheduler: sleep once, run once, exit.

$ErrorActionPreference = "Stop"
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$routine  = Join-Path $PSScriptRoot "routine.md"
$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$out = Join-Path $PSScriptRoot "run-$timestamp.txt"

# One-off timer: wait a short, fixed delay, then run exactly once.
$delaySeconds = 2
Write-Host "One-off timer: sleeping $delaySeconds`s before the single run..."
Start-Sleep -Seconds $delaySeconds

$prompt = Get-Content -Raw -LiteralPath $routine
Write-Host "Running routine once via 'opencode run'..."
& opencode run --model opencode/big-pickle --format json --dir $repoRoot $prompt *>&1 | Tee-Object -FilePath $out

Write-Host "One-off run complete. Full transcript written to: $out"
