# ---- NPU UI v2 (PS 5.1 compatible) ----
$ErrorActionPreference='Stop'
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
[Console]::OutputEncoding=[Text.Encoding]::UTF8

function T { (Get-Date).ToString('HH:mm:ss.fff') }

# Repo, paths
$Repo       = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
$ModelsRoot = Join-Path $Repo 'models\ov_npu_ready'
$GenCli     = Join-Path $Repo 'ai\cli\genai_run.py'
$TrainPy    = Join-Path $Repo 'ai\train\lora_sft.py'
$UseGen = Test-Path $GenCli
if(-not $UseGen){ [System.Windows.Forms.MessageBox]::Show("cli 스크립트 누락: $GenCli"); exit }

# Python
$PY = @(
  (Join-Path $Repo '.\.venv\Scripts\python.exe'),
  'python.exe','python'
) | Where-Object { Get-Command $_ -ErrorAction SilentlyContinue } | Select-Object -First 1
if(-not $PY){ [System.Windows.Forms.MessageBox]::Show('Python 실행기 없음(.venv 권장)'); exit }

# Offline env for child
$baseEnv = @{
  'HF_HUB_OFFLINE'='1'; 'TRANSFORMERS_OFFLINE'='1'; 'HF_DATASETS_OFFLINE'='1';
  'PYTHONIOENCODING'='utf-8'; 'PYTHONUTF8'='1'
}

# Model scan
function Test-OVDir([string]$d){
  (Test-Path (Join-Path $d 'openvino_model.xml')) -and
  (Test-Path (Join-Path $d 'openvino_tokenizer.xml')) -and
  (Test-Path (Join-Path $d 'openvino_detokenizer.xml'))
}
$Models=@()
if(Test-Path $ModelsRoot){
  Get-ChildItem $ModelsRoot -Directory | ? { Test-OVDir $_.FullName } | % { $Models += $_.FullName }
}

# ---- UI layout ----
$f = New-Object Windows.Forms.Form
$f.Text='NPU GenAI UI v2'
$f.Size=New-Object Drawing.Size(980,720)
$f.StartPosition='CenterScreen'

$tabs = New-Object Windows.Forms.TabControl
$tabs.Dock='Fill'
$f.Controls.Add($tabs)

# ========== Tab 1: Inference ==========
$tabInf = New-Object Windows.Forms.TabPage
$tabInf.Text='NPU 추론'
$tabs.TabPages.Add($tabInf)

# controls
$lblModel = New-Object Windows.Forms.Label; $lblModel.Text='Model Dir'; $lblModel.Location=New-Object Drawing.Point(12,15); $lblModel.AutoSize=$true
$cboModel = New-Object Windows.Forms.ComboBox; $cboModel.Location=New-Object Drawing.Point(90,12); $cboModel.Size=New-Object Drawing.Size(740,24); $cboModel.DropDownStyle='DropDownList'
if($Models.Count -gt 0){ $cboModel.Items.AddRange($Models); $cboModel.SelectedIndex=0 }
$btnBrowse = New-Object Windows.Forms.Button; $btnBrowse.Text='선택'; $btnBrowse.Location=New-Object Drawing.Point(840,10)

$lblDev = New-Object Windows.Forms.Label; $lblDev.Text='Device'; $lblDev.Location=New-Object Drawing.Point(12,48); $lblDev.AutoSize=$true
$cboDev = New-Object Windows.Forms.ComboBox; $cboDev.Location=New-Object Drawing.Point(90,45); $cboDev.Size=New-Object Drawing.Size(120,24)
@('NPU','AUTO','CPU') | % { [void]$cboDev.Items.Add($_) }; $cboDev.SelectedIndex=0

$lblTok = New-Object Windows.Forms.Label; $lblTok.Text='Max New Tokens'; $lblTok.Location=New-Object Drawing.Point(230,48); $lblTok.AutoSize=$true
$numTok = New-Object Windows.Forms.NumericUpDown; $numTok.Location=New-Object Drawing.Point(340,45); $numTok.Minimum=1; $numTok.Maximum=4096; $numTok.Value=256

$lblTpl = New-Object Windows.Forms.Label; $lblTpl.Text='템플릿'; $lblTpl.Location=New-Object Drawing.Point(430,48); $lblTpl.AutoSize=$true
$cboTpl = New-Object Windows.Forms.ComboBox; $cboTpl.Location=New-Object Drawing.Point(480,45); $cboTpl.Size=New-Object Drawing.Size(200,24)
$cboTpl.DropDownStyle='DropDownList'
$cboTpl.Items.Add('지시형(작업 명령)')
$cboTpl.Items.Add('요약형(핵심요약)')
$cboTpl.Items.Add('추출형(키워드/항목)')
$cboTpl.Items.Add('브레인스토밍(아이디어)')
$cboTpl.SelectedIndex=0
$btnIns = New-Object Windows.Forms.Button; $btnIns.Text='삽입'; $btnIns.Location=New-Object Drawing.Point(690,45)

$btnRun = New-Object Windows.Forms.Button; $btnRun.Text='실행'; $btnRun.Location=New-Object Drawing.Point(780,45)
$btnStop= New-Object Windows.Forms.Button; $btnStop.Text='중지'; $btnStop.Location=New-Object Drawing.Point(840,45)

$txtPrompt = New-Object Windows.Forms.TextBox; $txtPrompt.Multiline=$true; $txtPrompt.ScrollBars='Both'
$txtPrompt.Location=New-Object Drawing.Point(12,80); $txtPrompt.Size=New-Object Drawing.Size(930,160)
$txtPrompt.Text='NPU 확인 테스트'

$txtLog = New-Object Windows.Forms.TextBox; $txtLog.Multiline=$true; $txtLog.ScrollBars='Both'; $txtLog.ReadOnly=$true
$txtLog.Location=New-Object Drawing.Point(12,290); $txtLog.Size=New-Object Drawing.Size(930,340)

$pb = New-Object Windows.Forms.ProgressBar; $pb.Location=New-Object Drawing.Point(12,250); $pb.Size=New-Object Drawing.Size(700,20); $pb.Style='Blocks'
$lblState = New-Object Windows.Forms.Label; $lblState.Text='대기'; $lblState.Location=New-Object Drawing.Point(720,248); $lblState.AutoSize=$true
$lblElapsed = New-Object Windows.Forms.Label; $lblElapsed.Text='0.0s'; $lblElapsed.Location=New-Object Drawing.Point(860,248); $lblElapsed.AutoSize=$true

$btnLogDir = New-Object Windows.Forms.Button; $btnLogDir.Text='로그 폴더'; $btnLogDir.Location=New-Object Drawing.Point(12,640)
$btnExit = New-Object Windows.Forms.Button; $btnExit.Text='종료'; $btnExit.Location=New-Object Drawing.Point(872,640)

# add
$tabInf.Controls.AddRange(@($lblModel,$cboModel,$btnBrowse,$lblDev,$cboDev,$lblTok,$numTok,$lblTpl,$cboTpl,$btnIns,$btnRun,$btnStop,$txtPrompt,$pb,$lblState,$lblElapsed,$txtLog,$btnLogDir,$btnExit))

# timer
$sw = [System.Diagnostics.Stopwatch]::new()
$timer = New-Object Windows.Forms.Timer; $timer.Interval=200
$timer.Add_Tick({ if($sw.IsRunning){ $lblElapsed.Text = ('{0:N1}s' -f $sw.Elapsed.TotalSeconds) } })

# logging
$UiLogDir = Join-Path $PSScriptRoot 'logs'; New-Item $UiLogDir -ItemType Directory -Force | Out-Null
$uiLog = Join-Path $UiLogDir ('ui_{0:yyyyMMdd_HHmmss}.log' -f (Get-Date))

function Append-Log([string]$s){
  if([string]::IsNullOrWhiteSpace($s)){ return }
  $line = "[{0}] {1}" -f (T), $s
  $act=[System.Action[string]]{ param($t) $txtLog.AppendText($t + "`r`n") }
  if($txtLog.InvokeRequired){ $null=$txtLog.Invoke($act, @($line)) } else { $act.Invoke($line) }
  Add-Content -Path $uiLog -Value $line -Encoding UTF8
}
function Set-State([string]$s,[bool]$busy){
  $lblState.Text=$s
  if($busy){ $pb.Style='Marquee'; $pb.MarqueeAnimationSpeed=30; $sw.Restart(); $timer.Start() }
  else { $pb.Style='Blocks'; $pb.MarqueeAnimationSpeed=0; $timer.Stop(); $sw.Stop() }
}

# templates
function Get-Template([int]$i){
  switch($i){
    0 { "다음 작업을 수행하라. 제약: 간결, 단계별, 한국어.\n입력:\n" }
    1 { "다음 텍스트를 5줄 이하 핵심요약. 불필요 제거.\n텍스트:\n" }
    2 { "다음에서 항목을 추출하라. 키워드/항목/수치.\n텍스트:\n" }
    3 { "주제에 대한 아이디어 10개. 간단 근거 포함.\n주제:\n" }
  }
}

# browse
$btnBrowse.Add_Click({
  $dlg = New-Object System.Windows.Forms.FolderBrowserDialog
  $dlg.SelectedPath = $ModelsRoot
  if($dlg.ShowDialog() -eq 'OK'){
    if(Test-OVDir $dlg.SelectedPath){
      if(-not $cboModel.Items.Contains($dlg.SelectedPath)){ $null=$cboModel.Items.Add($dlg.SelectedPath) }
      $cboModel.Text=$dlg.SelectedPath
    } else {
      [System.Windows.Forms.MessageBox]::Show('openvino_model.xml/tokenizer/detokenizer 3종이 없는 폴더')
    }
  }
})

$btnIns.Add_Click({ $txtPrompt.Text = (Get-Template $cboTpl.SelectedIndex) })

# run/stop
$script:proc=$null
$btnRun.Add_Click({
  try{
    if($script:proc -and -not $script:proc.HasExited){ Append-Log '[WARN] 이미 실행 중'; return }
    $model=$cboModel.Text
    if([string]::IsNullOrWhiteSpace($model)){ Append-Log '모델 없음: models\ov_npu_ready 확인'; return }
    $args = @(
      '-u', $GenCli, '--model_dir', $model,
      '--device', $cboDev.Text,
      '--max_new_tokens', ([int]$numTok.Value).ToString(),
      '--prompt', $txtPrompt.Text
    )

    $psi=New-Object System.Diagnostics.ProcessStartInfo
    $psi.FileName=$PY
    $psi.WorkingDirectory=$Repo
    $psi.UseShellExecute=$false
    $psi.RedirectStandardOutput=$true
    $psi.RedirectStandardError=$true
    $psi.CreateNoWindow=$true
    $psi.Arguments = ($args | ForEach-Object {
      if($_ -match '[\s"`]'){ '"' + ($_ -replace '"','\"') + '"' } else { $_ }
    }) -join ' '
    foreach($k in $baseEnv.Keys){ $psi.EnvironmentVariables[$k]=$baseEnv[$k] }

    Append-Log ("[RUN] {0} {1}" -f $psi.FileName, $psi.Arguments)
    Set-State '실행 중' $true
    $script:proc=New-Object System.Diagnostics.Process
    $script:proc.StartInfo=$psi
    $script:proc.EnableRaisingEvents=$true
    $script:proc.add_OutputDataReceived({ param($s,$e) if($e.Data){ Append-Log $e.Data } })
    $script:proc.add_ErrorDataReceived({  param($s,$e) if($e.Data){ Append-Log $e.Data } })
    $script:proc.add_Exited({ param($s,$e) Append-Log ("[EXIT] code=" + $s.ExitCode); Set-State '대기' $false })
    [void]$script:proc.Start()
    $script:proc.BeginOutputReadLine()
    $script:proc.BeginErrorReadLine()
  } catch { Append-Log ('ERROR: ' + $_.Exception.Message); Set-State '오류' $false }
})

$btnStop.Add_Click({
  try{
    if($script:proc -and -not $script:proc.HasExited){
      $script:proc.Kill(); Append-Log '[STOP] 프로세스 강제 종료'
    } else { Append-Log '실행 중 아님' }
  } catch { Append-Log ('ERROR: ' + $_.Exception.Message) }
})

$btnLogDir.Add_Click({ Start-Process explorer.exe $UiLogDir })
$btnExit.Add_Click({ $f.Close() })

# ========== Tab 2: GPU 학습 ==========
$tabTr = New-Object Windows.Forms.TabPage
$tabTr.Text='GPU 학습(LoRA)'
$tabs.TabPages.Add($tabTr)

$lblBase = New-Object Windows.Forms.Label; $lblBase.Text='Base 모델/폴더'; $lblBase.Location='12,15'; $lblBase.AutoSize=$true
$txtBase = New-Object Windows.Forms.TextBox; $txtBase.Location='120,12'; $txtBase.Size='710,24'; $txtBase.Text='llmware/llama-3.2-1b-instruct'
$btnBase = New-Object Windows.Forms.Button; $btnBase.Text='선택'; $btnBase.Location='840,10'
$lblEp = New-Object Windows.Forms.Label; $lblEp.Text='Epochs'; $lblEp.Location='12,48'; $lblEp.AutoSize=$true
$numEp = New-Object Windows.Forms.NumericUpDown; $numEp.Location='120,45'; $numEp.Minimum=1; $numEp.Maximum=50; $numEp.Value=1
$lblSeq = New-Object Windows.Forms.Label; $lblSeq.Text='SeqLen'; $lblSeq.Location='200,48'; $lblSeq.AutoSize=$true
$numSeq = New-Object Windows.Forms.NumericUpDown; $numSeq.Location='260,45'; $numSeq.Minimum=256; $numSeq.Maximum=4096; $numSeq.Value=1024
$lblPrec = New-Object Windows.Forms.Label; $lblPrec.Text='Precision'; $lblPrec.Location='340,48'; $lblPrec.AutoSize=$true
$cboPrec = New-Object Windows.Forms.ComboBox; $cboPrec.Location='410,45'; $cboPrec.Size='120,24'; @('fp16','bf16','fp32') | % { [void]$cboPrec.Items.Add($_) }; $cboPrec.SelectedIndex=0
$lblRN = New-Object Windows.Forms.Label; $lblRN.Text='RunName'; $lblRN.Location='540,48'; $lblRN.AutoSize=$true
$txtRN = New-Object Windows.Forms.TextBox; $txtRN.Location='610,45'; $txtRN.Size='220,24'; $txtRN.Text=("run_{0:yyyyMMdd_HHmm}" -f (Get-Date))
$btnTrain = New-Object Windows.Forms.Button; $btnTrain.Text='학습 시작'; $btnTrain.Location='840,45'

$txtLogT = New-Object Windows.Forms.TextBox; $txtLogT.Multiline=$true; $txtLogT.ScrollBars='Both'; $txtLogT.ReadOnly=$true
$txtLogT.Location='12,80'; $txtLogT.Size='930,550'

$tabTr.Controls.AddRange(@($lblBase,$txtBase,$btnBase,$lblEp,$numEp,$lblSeq,$numSeq,$lblPrec,$cboPrec,$lblRN,$txtRN,$btnTrain,$txtLogT))

function Append-LogT([string]$s){
  if([string]::IsNullOrWhiteSpace($s)){ return }
  $line="[{0}] {1}" -f (T), $s
  $act=[System.Action[string]]{ param($t) $txtLogT.AppendText($t + "`r`n") }
  if($txtLogT.InvokeRequired){ $null=$txtLogT.Invoke($act, @($line)) } else { $act.Invoke($line) }
  Add-Content -Path (Join-Path $UiLogDir 'train.log') -Value $line -Encoding UTF8
}

$script:procT=$null
$btnBase.Add_Click({
  $dlg = New-Object System.Windows.Forms.FolderBrowserDialog
  if($dlg.ShowDialog() -eq 'OK'){ $txtBase.Text=$dlg.SelectedPath }
})

$btnTrain.Add_Click({
  try{
    if(-not (Test-Path $TrainPy)){ Append-LogT "학습 스크립트 없음: $TrainPy"; return }
    if($script:procT -and -not $script:procT.HasExited){ Append-LogT '[WARN] 이미 학습 중'; return }
    $outDir = Join-Path $Repo ("models\hf_finetuned\" + $txtRN.Text)

    $args=@('-u', $TrainPy, '--base', $txtBase.Text, '--out_dir', $outDir,
            '--epochs', ([int]$numEp.Value).ToString(), '--seq_len', ([int]$numSeq.Value).ToString(),
            '--precision', $cboPrec.Text)
    $psi=New-Object System.Diagnostics.ProcessStartInfo
    $psi.FileName=$PY; $psi.WorkingDirectory=$Repo
    $psi.UseShellExecute=$false; $psi.RedirectStandardOutput=$true; $psi.RedirectStandardError=$true; $psi.CreateNoWindow=$true
    $psi.Arguments = ($args | ForEach-Object { if($_ -match '[\s"`]'){ '"' + ($_ -replace '"','\"') + '"' } else { $_ } }) -join ' '
    foreach($k in $baseEnv.Keys){ $psi.EnvironmentVariables[$k]=$baseEnv[$k] }

    Append-LogT ("[RUN] {0} {1}" -f $psi.FileName, $psi.Arguments)
    $script:procT=New-Object System.Diagnostics.Process
    $script:procT.StartInfo=$psi
    $script:procT.EnableRaisingEvents=$true
    $script:procT.add_OutputDataReceived({ param($s,$e) if($e.Data){ Append-LogT $e.Data } })
    $script:procT.add_ErrorDataReceived({  param($s,$e) if($e.Data){ Append-LogT $e.Data } })
    $script:procT.add_Exited({ param($s,$e) Append-LogT ("[EXIT] code=" + $s.ExitCode) })
    [void]$script:procT.Start(); $script:procT.BeginOutputReadLine(); $script:procT.BeginErrorReadLine()
  } catch { Append-LogT ('ERROR: ' + $_.Exception.Message) }
})

# show
$timer.Start()
[void]$f.ShowDialog()
# ---- End ----
