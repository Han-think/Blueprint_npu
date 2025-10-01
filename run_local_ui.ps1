param(
  [int]$Port = 7860,
  [string]$Wrap = ".\run_ui_wrap.ps1",
  [string]$UiPy = ".\ai\ui\dual_device_ui.py"
)
$ErrorActionPreference='Stop'

function Get-Py {
  $p = ".\.venv\Scripts\python.exe"
  if (Test-Path $p) { return (Resolve-Path $p).Path }
  $cmd = Get-Command python -ErrorAction SilentlyContinue
  if ($cmd) { return $cmd.Path }
  throw "Python not found (.venv 또는 시스템 python 필요)"
}
$PY = Get-Py

# UTF-8 & Gradio 로컬 루프백 바인딩
$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"
$env:GRADIO_SERVER_NAME = "127.0.0.1"

# 포트 가용성 스캔
function Get-FreePort([int]$start,[int]$count=20){
  for($p=$start; $p -lt ($start+$count); $p++){
    $l = New-Object System.Net.Sockets.TcpListener([System.Net.IPAddress]::Loopback,$p)
    try { $l.Start(); $l.Stop(); return $p } catch {}
  }
  throw "사용 가능한 포트를 찾지 못했습니다 (start=$start)."
}
$Port = Get-FreePort -start $Port
$env:GRADIO_SERVER_PORT = "$Port"

# gradio 보장 (pip show로 검사)
& $PY -m pip show gradio *> $null
if ($LASTEXITCODE -ne 0) { & $PY -m pip install -q gradio }

# 실행: run_ui_wrap.ps1 우선, 없으면 dual_device_ui.py, 둘 다 없으면 폴백 UI
$proc = $null
if (Test-Path $Wrap) {
  $proc = Start-Process powershell -ArgumentList @(
    "-NoLogo","-NoProfile","-ExecutionPolicy","Bypass",
    "-File",$Wrap,"-Net","local","-Port",$Port
  ) -PassThru -WindowStyle Hidden
}
elseif (Test-Path $UiPy) {
  $proc = Start-Process $PY -ArgumentList @($UiPy) -PassThru -WindowStyle Hidden
}
else {
  $mini = Join-Path $env:TEMP "mini_ui.py"
  @"
import os, gradio as gr
def echo(x): return x
gr.Interface(fn=echo, inputs='text', outputs='text', title='Blueprint UI (fallback)').launch(
    server_name='127.0.0.1',
    server_port=int(os.environ.get('GRADIO_SERVER_PORT','7860'))
)
"@ | Set-Content $mini -Encoding UTF8
  $proc = Start-Process $PY -ArgumentList @($mini) -PassThru -WindowStyle Hidden
}

# 서버 대기 후 브라우저 오픈 (127.0.0.1로 강제)
$ok=$false
for($i=0;$i -lt 60;$i++){
  try {
    Invoke-WebRequest -Uri "http://127.0.0.1:$Port" -UseBasicParsing -TimeoutSec 1 | Out-Null
    $ok=$true; break
  } catch { Start-Sleep -Milliseconds 500 }
}
if ($ok) {
  Start-Process "http://127.0.0.1:$Port"
  Write-Host "✅ UI ready  ->  http://127.0.0.1:$Port"
} else {
  Write-Warning "UI가 포트 $Port 에서 응답하지 않습니다. 로그를 확인하세요."
}
