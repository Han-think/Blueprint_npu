$ErrorActionPreference="Stop"
$PORT = 9035
$PY = (Get-Command py -EA SilentlyContinue).Source; if(-not $PY){ $PY=(Get-Command python -EA SilentlyContinue).Source }
& $PY -m pip install -U -r (Join-Path $PSScriptRoot "..\requirements.txt")
powershell -ExecutionPolicy Bypass -File (Join-Path $PSScriptRoot "download_models.ps1")
Get-Process -Name python,uvicorn -EA SilentlyContinue | Stop-Process -Force -EA SilentlyContinue
& $PY -m uvicorn app.workbench:app --host 127.0.0.1 --port $PORT
