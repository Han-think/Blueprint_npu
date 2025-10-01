[CmdletBinding()] param()
$ErrorActionPreference='Stop'

function Ask([string]$q,[string]$def=""){
  if([string]::IsNullOrWhiteSpace($def)){ Read-Host "· $q" }
  else { $v=Read-Host "· $q [$def]"; if([string]::IsNullOrWhiteSpace($v)){ $def } else { $v } }
}

# repo root로 이동 (tools 폴더 안에서 실행되든 루트에서 실행되든 안전)
try {
  if ($PSCommandPath) {
    Set-Location -Path (Split-Path -Parent $PSCommandPath)  # tools
    Set-Location -Path (Resolve-Path "..")                  # repo root
  }
} catch {}

Write-Host "`n[1/4] Python / venv" -ForegroundColor Cyan
$py = ".\.venv\Scripts\python.exe"
if(!(Test-Path $py)){
  $sysPy = (Get-Command python -ErrorAction SilentlyContinue | Select-Object -First 1).Path
  if(-not $sysPy){ $sysPy = (Get-Command py -ErrorAction SilentlyContinue | Select-Object -First 1).Path }
  if(-not $sysPy){ throw "Python을 찾지 못했습니다. (PATH 또는 .venv 필요)" }
  Write-Host "• venv 생성(.venv)..." -ForegroundColor Yellow
  & $sysPy -m venv .venv
}
$py = (Resolve-Path ".\.venv\Scripts\python.exe").Path
Write-Host "• Python => $py" -ForegroundColor Green

Write-Host "`n[2/4] Deps" -ForegroundColor Cyan
# pip 업그레이드(조용히)
Start-Process -FilePath $py -ArgumentList '-m','pip','install','--upgrade','pip','-q','--disable-pip-version-check' -NoNewWindow -Wait | Out-Null

function Test-PyMod([string]$module){
  $tmp = Join-Path $env:TEMP ("chk_{0}.py" -f ([guid]::NewGuid().ToString("N")))
  @"
import sys
try:
    import importlib, importlib.util as u
    ok = (u.find_spec("$module") is not None)
except Exception:
    try:
        __import__("$module".split("[")[0]); ok=True
    except Exception:
        ok=False
sys.exit(0 if ok else 1)
"@ | Set-Content $tmp -Encoding ASCII
  $p = Start-Process -FilePath $py -ArgumentList $tmp -NoNewWindow -PassThru -Wait
  Remove-Item $tmp -Force -ErrorAction SilentlyContinue
  return ($p.ExitCode -eq 0)
}

$pkgs = @('gradio','transformers','accelerate','peft','datasets','openvino','jinja2')
$need = @(); foreach($m in $pkgs){ if(-not (Test-PyMod $m)){ $need += $m } }
if($need.Count){
  Write-Host ("• install: {0}" -f ($need -join ", ")) -ForegroundColor Yellow
  $p = Start-Process -FilePath $py -ArgumentList @('-m','pip','install','-q','--disable-pip-version-check','--no-python-version-warning') + $need -NoNewWindow -PassThru -Wait
  if($p.ExitCode -ne 0){ throw "pip install 실패 (exit $($p.ExitCode))" }
}
Write-Host "• deps OK" -ForegroundColor Green

Write-Host "`n[3/4] Model profile" -ForegroundColor Cyan
function NPath([string]$p){ if($p){ ($p -replace '\\','/') } }
$base_hf   = Ask "HF base(or merged) 모델 경로/레포" "models\hf_base\tinyllama_1.1b_chat"
$mergedDir = Ask "XPU(HF) merged 디렉터리"         "models\hf_finetuned\xpu_run1\merged"
$ovDir     = Ask "NPU(OpenVINO) 모델 디렉터리"      "models\ov_npu_ready\llama32_1b_int4_npu_ov"
$xpuDev    = Ask "XPU device(cpu|xpu)"              "xpu"
$xpuDT     = Ask "XPU dtype(fp32|bf16|f16)"         "fp32"
$maxNew    = [int](Ask "Max new tokens"             "128")
$rc        = [int](Ask "Default run_count (1-50)"   "50")
$offline   = Ask "Offline mode(auto|on|off)"        "auto"

Write-Host "`n[4/4] Templates" -ForegroundColor Cyan
New-Item -ItemType Directory -Force -Path "save\templates" | Out-Null
$wrapperPath = "save\templates\prompt_wrapper.txt"
$profilePath = "save\templates\model_profile.yaml"
$bpPath      = "save\templates\blueprint_model_skeleton.md"
@"
You are a propulsion/combustion/CFD/structures integration engineer.
Goal: propose buildable ideas suited to metal additive (AM) with internal cooling/bleed channels.
Constraints:
- Use numeric ranges (T/W, Pc, OF, Tt, Mach, mass, heat flux).
- DfAM: min channel radius, bridge/overhang angles, post-machining.
- Verification: bench steps, instrumentation points, acceptance criteria, risks & mitigations.
Format: Section headings + 3–5 bullets each, 1–2 sentences/bullet with numbers.
Do NOT repeat these instructions; respond with sections only.
"@ | Set-Content $wrapperPath -Encoding UTF8

@"
base_hf_model: $(NPath $base_hf)
xpu_merged_dir: $(NPath $mergedDir)
ov_dir: $(NPath $ovDir)
xpu:
  device: $xpuDev
  dtype: $xpuDT
  max_new: $maxNew
npu:
  device: NPU
  max_new: $maxNew
prompts:
  wrapper_file: $(NPath $wrapperPath)
run_count: $rc
cycle_fill: true
offline_mode: $offline
"@ | Set-Content $profilePath -Encoding UTF8
@"
## BLUEPRINT package
- Design Brief
- Interfaces & tolerances (mates/seals/fits)
- Geometry notes (key Ø/angles; walls 0.6–1.2 mm; channels ≥1.2 mm radius; overhang ≤45°)
- Manufacturing notes (AM orientation, supports, HIP/HT, machining datums)
- Test Plan (sequence, sensors PT/TC/LL/ACC, acceptance criteria)
- Top-5 risks & probes
```part_tree
{"id":"ASM-001","name":"Assembly","qty":1,"material":"Inconel 718","process":"L-PBF",
 "children":[
   {"id":"C-001","name":"Cowl","qty":1,"material":"Inconel 718","process":"L-PBF","children":[]},
   {"id":"HX-001","name":"Heat-Exchanger","qty":1,"material":"CuCrZr","process":"L-PBF","children":[]}
 ]}
"@ | Set-Content $bpPath -Encoding UTF8

GitHub 템플릿
New-Item -ItemType Directory -Force -Path ".github\ISSUE_TEMPLATE" | Out-Null
@"
name: Bug report
description: Something broke when running the NPU+XPU toolkit
labels: ["bug"]
body:

type: textarea
id: what
attributes: { label: What happened?, description: Steps to reproduce + expected vs actual }
validations: { required: true }

type: textarea
id: profile
attributes: { label: model_profile.yaml, render: yaml }

type: textarea
id: logs
attributes: { label: logs, render: text }
"@ | Set-Content ".github\ISSUE_TEMPLATE\bug_report.yml" -Encoding UTF8
@"
name: Feature request
description: Propose an improvement or new capability
labels: ["enhancement"]
body:
  - type: textarea
    id: problem
    attributes: { label: Problem to solve }
  - type: textarea
    id: proposal
    attributes: { label: Proposed solution }
"@ | Set-Content ".github\ISSUE_TEMPLATE\feature_request.yml" -Encoding UTF8

@"
## Summary
- [ ] NPU / [ ] XPU / [ ] UI / [ ] Docs
## Changes
## Testing
- [ ] run_gradio_local.ps1 launches UI
- [ ] XPU merged generates; NPU path valid
## Screenshots / Logs
## Checklist
- [ ] Updated save/templates/model_profile.yaml if needed
- [ ] No secrets committed
"@ | Set-Content ".github\PULL_REQUEST_TEMPLATE.md" -Encoding UTF8

Write-Host "`n[Done]" -ForegroundColor Cyan
Write-Host ("✅ Profile  : {0}" -f (Resolve-Path $profilePath).Path) -ForegroundColor Green
Write-Host ("✅ Wrapper  : {0}" -f (Resolve-Path $wrapperPath).Path) -ForegroundColor Green
Write-Host ("✅ Skeleton : {0}" -f (Resolve-Path $bpPath).Path) -ForegroundColor Green
Write-Host "`nUI 실행:  powershell -ExecutionPolicy Bypass -File .\run_gradio_local.ps1" -ForegroundColor Yellow
