$ErrorActionPreference = 'Stop'
$python = '.\.venv\Scripts\python.exe'
if (-not (Test-Path $python)) { throw 'Run uv venv --python 3.12 .venv, then uv pip install --python .venv\Scripts\python.exe -e . first' }
& $python -m unittest discover -s tests -q
if ($LASTEXITCODE -ne 0) { throw 'Unit tests failed' }
& $python -m radar.service --mode demo --database-url .\radar-local.sqlite3
if ($LASTEXITCODE -ne 0) { throw 'Offline integration smoke test failed' }
Write-Host 'OFFLINE TESTS COMPLETE: NO LIVE TRADING / NO OPPORTUNITY ALERTS'
