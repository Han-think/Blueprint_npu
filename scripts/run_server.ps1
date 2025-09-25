$ErrorActionPreference="Stop"
$PORT=9035
$PY=(Get-Command py -EA SilentlyContinue).Source; if(-not $PY){$PY=(Get-Command python -EA SilentlyContinue).Source}; if(-not $PY){$PY="$env:LOCALAPPDATA\Programs\Python\Python311\python.exe"}
if(Test-Path .\requirements.txt){ & $PY -m pip install -U -r .\requirements.txt } else { & $PY -m pip install -U fastapi uvicorn pydantic numpy trimesh }
Get-Process -Name uvicorn,python -EA SilentlyContinue | Stop-Process -Force -EA SilentlyContinue
$proc = Start-Process -FilePath $PY -ArgumentList @('-m','uvicorn','app.workbench:app','--host','127.0.0.1','--port',$PORT) -PassThru
for($i=0;$i -lt 60;$i++){ try{ Invoke-RestMethod "http://127.0.0.1:$PORT/wb/health" -TimeoutSec 1 | Out-Null; 'ready'; break } catch { Start-Sleep -s 1 } }
