$ErrorActionPreference="Stop"
$PORT = 9035
$PY = (Get-Command py -EA SilentlyContinue).Source
if(-not $PY){ $PY = (Get-Command python -EA SilentlyContinue).Source }
if(-not $PY){ $PY = "$env:LOCALAPPDATA\Programs\Python\Python311\python.exe" }

& $PY -m pip install -U fastapi==0.111.0 uvicorn==0.30.0 pydantic==2.7.0 numpy==2.2.6 trimesh -q

Get-Process -Name python,uvicorn -EA SilentlyContinue | Stop-Process -Force -EA SilentlyContinue
& $PY -m uvicorn app.workbench:app --host 127.0.0.1 --port $PORT
