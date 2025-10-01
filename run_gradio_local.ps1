param([int]$Port=7860)
$ErrorActionPreference='Stop'

function Get-Py {
  $p = ".\.venv\Scripts\python.exe"
  if (Test-Path $p) { return (Resolve-Path $p).Path }
  $cmd = Get-Command python -ErrorAction SilentlyContinue
  if ($cmd) { return $cmd.Path }
  throw "Python not found (.venv 또는 시스템 python 필요)"
}
$PY = Get-Py
$env:PYTHONUTF8="1"; $env:PYTHONIOENCODING="utf-8"; $env:GRADIO_SERVER_NAME="127.0.0.1"

function Get-FreePort([int]$start,[int]$count=30){
  for($p=$start; $p -lt ($start+$count); $p++){
    $l=New-Object System.Net.Sockets.TcpListener([System.Net.IPAddress]::Loopback,$p)
    try{$l.Start();$l.Stop();return $p}catch{}
  }
  throw "사용 가능한 포트를 찾지 못했습니다 (start=$start)."
}
$Port = Get-FreePort -start $Port
$env:GRADIO_SERVER_PORT="$Port"

# gradio 체크/설치 (임시 파일로 실행)
$tmp = Join-Path $env:TEMP ("chk_gradio_{0}.py" -f ([guid]::NewGuid().ToString("N")))
@"
import sys
try:
    import gradio  # noqa
    sys.exit(0)
except Exception:
    sys.exit(1)
"@ | Set-Content $tmp -Encoding ASCII
$p = Start-Process -FilePath $PY -ArgumentList $tmp -NoNewWindow -PassThru -Wait
Remove-Item $tmp -Force -ErrorAction SilentlyContinue
if ($p.ExitCode -ne 0){
  $p = Start-Process -FilePath $PY -ArgumentList '-m','pip','install','-q','--disable-pip-version-check','--no-python-version-warning','gradio' -NoNewWindow -PassThru -Wait
  if ($p.ExitCode -ne 0){ throw "gradio 설치 실패 (pip exit $($p.ExitCode))" }
}

# 앱 실행
$APP = (Resolve-Path '.\ai\ui\blueprint_batch_ui.py').Path
$proc = Start-Process $PY -ArgumentList @($APP) -PassThru -WindowStyle Hidden

# 서버 대기 -> 브라우저 오픈
$ok=$false
for($i=0;$i -lt 60;$i++){
  try{ Invoke-WebRequest -Uri "http://127.0.0.1:$Port" -UseBasicParsing -TimeoutSec 1 | Out-Null; $ok=$true; break }catch{ Start-Sleep -Milliseconds 500 }
}
if($ok){ Start-Process "http://127.0.0.1:$Port"; Write-Host "✅ UI ready  ->  http://127.0.0.1:$Port" }
else{ Write-Warning "UI가 포트 $Port 에서 응답하지 않습니다. 로그 확인 필요." }
