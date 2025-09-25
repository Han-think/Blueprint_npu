$ErrorActionPreference="Stop"
$PORT = 9035
$PY = (Get-Command py -EA SilentlyContinue).Source
if(-not $PY){ $PY = (Get-Command python -EA SilentlyContinue).Source }
if(-not $PY){ throw "python이 필요합니다." }

& $PY -m pip install -U pip | Out-Null
& $PY -m pip install -U -r (Join-Path $PSScriptRoot "..\requirements.txt")

Get-Process -Name python,uvicorn -EA SilentlyContinue | Stop-Process -Force -EA SilentlyContinue
& $PY -m uvicorn app.workbench:app --host 127.0.0.1 --port $PORT
