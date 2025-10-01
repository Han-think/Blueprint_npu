$ErrorActionPreference='Stop'
[Console]::OutputEncoding=[Text.Encoding]::UTF8
$SRC = (Get-Location).Path
$DST = Join-Path $SRC "release\GITHUB_MIN"
if(Test-Path $DST){ Remove-Item -Recurse -Force $DST }
New-Item -ItemType Directory -Force -Path $DST | Out-Null

$keep = @(
  ".gitattributes",".gitignore","README.md","LICENSE",
  "README_MIN.md","VERSION.txt","SCHEMA.md",
  "configs\models.txt",
  "prompts\sys_template.txt","prompts\usr_template.txt","prompts\prompts_topics.txt",
  "ai\cli\batch_dual_v3.py","ai\cli\chat.py","ai\cli\genai_run.py",
  "ai\ui\quick_ui.py",
  "scripts\hf_pull_ov_models.py",
  "tools\make_github_min.ps1","tools\validate_outputs.py",
  "run_*.ps1","run_*.bat","run_gradio_local.ps1","run_gradio_local.bat",
  "docs\**\*.md","docs\AI_Design_Pipeline.txt","docs\powershell_ui_common_issues.txt",
  ".github\workflows\qa.yml",".env.template","requirements-ov.txt","requirements-ml.txt"
)

$dropDirs = @(".venv","models","logs","data","save","__pycache__",".git","BluePrint_New\.git")

function Should-Skip($p){ foreach($d in $dropDirs){ if($p -like (Join-Path $SRC "$d*")){ return $true } } return $false }
function Copy-Keep{
  param([string[]]$Patterns)
  foreach($pat in $Patterns){
    $items = Get-ChildItem -Path (Join-Path $SRC ".") -Recurse -File -ErrorAction SilentlyContinue |
      Where-Object {
        $rel = $_.FullName.Substring($SRC.Length).TrimStart('\')
        ($rel -like $pat) -and -not (Should-Skip $_.FullName)
      }
    foreach($it in $items){
      $rel = $it.FullName.Substring($SRC.Length).TrimStart('\')
      $out = Join-Path $DST $rel
      New-Item -ItemType Directory -Force -Path (Split-Path $out) | Out-Null
      Copy-Item $it.FullName $out -Force
    }
  }
}

Copy-Keep -Patterns $keep

$readme = Join-Path $DST "README_MIN.md"
@"
# Blueprint_npu (minimal)
- NPU(OpenVINO) + XPU(Transformers) batch runner v3
- JSONL/MD/CSV + QA, topic-only prompts, no models included

## Quickstart
python -m venv .venv && .\.venv\Scripts\python.exe -m pip install -U pip
.\.venv\Scripts\python.exe -m pip install openvino==2025.3.* openvino-genai==2025.3.* transformers optimum-intel huggingface_hub rich gradio pandas
# edit configs\models.txt
.\.venv\Scripts\python.exe ai\cli\batch_dual_v3.py --ov_key phi4mini_ov --hf_key hf_small --topics prompts\prompts_topics.txt --sys_template prompts\sys_template.txt --usr_template prompts\usr_template.txt --ov_device NPU --hf_device xpu --jobs 1 --limit 30
# view
.\.venv\Scripts\python.exe ai\ui\quick_ui.py
"@ | Set-Content -Encoding UTF8 $readme

$ver = (git rev-parse --short HEAD 2>$null); if(-not $ver){ $ver="untracked" }
"commit=$ver`ndate=$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss K')" | Set-Content -Encoding UTF8 (Join-Path $DST "VERSION.txt")

$manifest = Join-Path $DST "MANIFEST_SHA256.txt"
Get-ChildItem -Path $DST -Recurse -File | ForEach-Object {
  $hash = Get-FileHash $_.FullName -Algorithm SHA256
  '{0}  {1}' -f $hash.Hash,$_.FullName.Substring($DST.Length).TrimStart('\')
} | Set-Content -Encoding ASCII $manifest

Write-Host "OK -> $DST"
