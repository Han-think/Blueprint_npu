$ErrorActionPreference="Stop"
$PORT = 9035
$PY = (Get-Command py -EA SilentlyContinue).Source
if(-not $PY){ $PY = (Get-Command python -EA SilentlyContinue).Source }
if(-not $PY){ $PY = "$env:LOCALAPPDATA\Programs\Python\Python311\python.exe" }

# 의존성 최소 설치
& $PY -m pip install -U fastapi uvicorn pydantic numpy trimesh | Out-Null

# 기존 uvicorn 종료
Get-Process -Name python,uvicorn -EA SilentlyContinue | Stop-Process -Force -EA SilentlyContinue

# 포그라운드 실행
& $PY -m uvicorn app.workbench:app --host 127.0.0.1 --port $PORT
