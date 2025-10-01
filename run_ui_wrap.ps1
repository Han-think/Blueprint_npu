param(
  [string]$Py = ".\.venv\Scripts\python.exe",
  [string]$Ui = ".\ai\ui\dual_device_ui.py",
  [string]$NpuModel = ".\models\ov_npu_ready\llama32_1b_int4_npu_ov",
  [string]$XpuModel = ".\models\hf_finetuned\xpu_run1\merged",
  [int]$Port = 7860,
  [ValidateSet('auto','online','offline')] [string]$Net = 'auto'
)
$ErrorActionPreference='Stop'
$env:PYTHONUTF8='1'; $env:PYTHONIOENCODING='utf-8'

# 인터넷 가용성 → 오프라인 플래그
$env:HF_HUB_OFFLINE=''; $env:TRANSFORMERS_OFFLINE=''; $env:HF_DATASETS_OFFLINE=''
$offline = $false
if ($Net -eq 'offline') { $offline = $true }
elseif ($Net -eq 'auto') {
  try { $ok = Test-Connection -ComputerName huggingface.co -Count 1 -Quiet } catch { $ok = $false }
  if (-not $ok) { $offline = $true }
}
if ($offline) {
  $env:HF_HUB_OFFLINE='1'; $env:TRANSFORMERS_OFFLINE='1'; $env:HF_DATASETS_OFFLINE='1'
}

if (!(Test-Path $Ui)) { throw "UI 스크립트가 없습니다: $Ui" }
if (!(Test-Path $NpuModel)) { Write-Warning "NPU 모델 경로 없음: $NpuModel" }
if (!(Test-Path $XpuModel)) { Write-Warning "XPU 모델 경로 없음: $XpuModel" }

& $Py $Ui --py $Py --gen ".\ai\cli\genai_run.py" `
  --npu_model $NpuModel --xpu_model $XpuModel --port $Port $(if($offline){'--offline'})
