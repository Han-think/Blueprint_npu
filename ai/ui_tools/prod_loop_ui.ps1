$ErrorActionPreference="Stop"
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
[Windows.Forms.Application]::EnableVisualStyles()

$AI   = Split-Path -Parent $PSScriptRoot
$ROOT = Split-Path -Parent $AI
$CLI  = Join-Path $ROOT "ai\cli"
$PY   = Join-Path $ROOT ".\.venv\Scripts\python.exe"

$ART  = Join-Path $ROOT "artifacts"
$REC  = Join-Path $ART  "recent"
$BEST = Join-Path $ART  "best"
$WORST= Join-Path $ART  "worst"
$DATA = Join-Path $ROOT "data\training"
$RUNPY= Join-Path $CLI  "genai_run.py"
$STLPY= Join-Path $CLI  "gen3d_stub.py"

function Get-ModelDirs{
  $roots = @(
    (Join-Path $ROOT "models\ov_npu_ready"),
    (Join-Path $ROOT "models\ov_static")
  ) | Where-Object { Test-Path $_ }
  $out = New-Object System.Collections.ArrayList
  foreach($r in $roots){
    Get-ChildItem -Path $r -Directory -Recurse -EA SilentlyContinue |
      ForEach-Object {
        $xml = Join-Path $_.FullName "openvino_model.xml"
        if(Test-Path $xml){ [void]$out.Add($_.FullName) }
      }
  }
  return $out
}

function Q([string]$s){ if($s -match '\s|["]'){ '"'+($s -replace '"','\"')+'"' } else { $s } }

function Prune-Recent {
  $dirs = Get-ChildItem $REC -Directory -EA SilentlyContinue | Sort-Object CreationTime -Descending
  $keep = 10
  if($dirs.Count -gt $keep){
    $dirs[$keep..($dirs.Count-1)] | ForEach-Object { Remove-Item $_.FullName -Recurse -Force -EA SilentlyContinue }
  }
}

# ---- UI ----
$f = New-Object Windows.Forms.Form
$f.Text = "NPU 생산 파이프라인 (4모델 동시)"
$f.StartPosition="CenterScreen"
$f.Width=1200; $f.Height=800
$f.Font=New-Object System.Drawing.Font('맑은 고딕',9)

# 상단 공통 파라미터
$top = New-Object Windows.Forms.TableLayoutPanel
$top.Dock='Top'; $top.Height=80; $top.ColumnCount=10
foreach($w in 35,8,8,8,8,8,8,8,4,5){ $top.ColumnStyles.Add((New-Object Windows.Forms.ColumnStyle([Windows.Forms.SizeType]::Percent,$w))) }

$lblPrompt = New-Object Windows.Forms.Label; $lblPrompt.Text="프롬프트"; $lblPrompt.Dock='Fill'; $lblPrompt.TextAlign='MiddleRight'
$txtPrompt = New-Object Windows.Forms.TextBox; $txtPrompt.Dock='Fill'
$cbDev = New-Object Windows.Forms.ComboBox; $cbDev.Dock='Fill'; @("NPU","AUTO","GPU","CPU") | % { [void]$cbDev.Items.Add($_) }; $cbDev.SelectedIndex=0
$lblTok = New-Object Windows.Forms.Label; $lblTok.Text="토큰"; $lblTok.Dock='Fill'; $lblTok.TextAlign='MiddleRight'
$nudTok = New-Object Windows.Forms.NumericUpDown; $nudTok.Minimum=16; $nudTok.Maximum=4096; $nudTok.Value=256; $nudTok.Dock='Fill'
$lblT = New-Object Windows.Forms.Label; $lblT.Text="Temp"; $lblT.Dock='Fill'; $lblT.TextAlign='MiddleRight'
$nudT = New-Object Windows.Forms.NumericUpDown; $nudT.DecimalPlaces=2; $nudT.Increment=0.05; $nudT.Minimum=0; $nudT.Maximum=2; $nudT.Value=0.7; $nudT.Dock='Fill'
$lblTopP = New-Object Windows.Forms.Label; $lblTopP.Text="TopP"; $lblTopP.Dock='Fill'; $lblTopP.TextAlign='MiddleRight'
$nudTopP = New-Object Windows.Forms.NumericUpDown; $nudTopP.DecimalPlaces=2; $nudTopP.Increment=0.05; $nudTopP.Minimum=0; $nudTopP.Maximum=1; $nudTopP.Value=0.9; $nudTopP.Dock='Fill'
$lblTopK = New-Object Windows.Forms.Label; $lblTopK.Text="TopK"; $lblTopK.Dock='Fill'; $lblTopK.TextAlign='MiddleRight'
$nudTopK = New-Object Windows.Forms.NumericUpDown; $nudTopK.Minimum=1; $nudTopK.Maximum=1000; $nudTopK.Value=50; $nudTopK.Dock='Fill'
$btnRunAll = New-Object Windows.Forms.Button; $btnRunAll.Text="모두 실행"; $btnRunAll.Dock='Fill'
$btnStopAll = New-Object Windows.Forms.Button; $btnStopAll.Text="모두 중지"; $btnStopAll.Dock='Fill'

$top.Controls.Add($lblPrompt,0,0); $top.Controls.Add($txtPrompt,0,0); $top.SetColumnSpan($txtPrompt,1)
$top.Controls.Add($cbDev,1,0)
$top.Controls.Add($lblTok,2,0);  $top.Controls.Add($nudTok,3,0)
$top.Controls.Add($lblT,4,0);    $top.Controls.Add($nudT,5,0)
$top.Controls.Add($lblTopP,6,0); $top.Controls.Add($nudTopP,7,0)
$top.Controls.Add($lblTopK,8,0); $top.Controls.Add($nudTopK,9,0)

# 모델 패널 생성 함수
$procs = @{}
function New-ModelPane([int]$idx){
  $g = New-Object Windows.Forms.GroupBox
  $g.Text = "모델 #$idx"; $g.Dock='Fill'

  $tbl = New-Object Windows.Forms.TableLayoutPanel
  $tbl.Dock='Fill'; $tbl.RowCount=4; $tbl.ColumnCount=4
  foreach($w in 55,15,15,15){ $tbl.ColumnStyles.Add((New-Object Windows.Forms.ColumnStyle([Windows.Forms.SizeType]::Percent,$w))) }
  $tbl.RowStyles.Add((New-Object Windows.Forms.RowStyle([Windows.Forms.SizeType]::Absolute,28)))
  $tbl.RowStyles.Add((New-Object Windows.Forms.RowStyle([Windows.Forms.SizeType]::Absolute,10)))
  $tbl.RowStyles.Add((New-Object Windows.Forms.RowStyle([Windows.Forms.SizeType]::Percent,100)))
  $tbl.RowStyles.Add((New-Object Windows.Forms.RowStyle([Windows.Forms.SizeType]::Absolute,30)))

  $cb = New-Object Windows.Forms.ComboBox; $cb.Dock='Fill'; $cb.DropDownStyle='DropDownList'
  (Get-ModelDirs) | % { [void]$cb.Items.Add($_) }; if($cb.Items.Count -gt 0){ $cb.SelectedIndex = [Math]::Min($idx-1, $cb.Items.Count-1) }

  $btnScan = New-Object Windows.Forms.Button; $btnScan.Text="재검색"; $btnScan.Dock='Fill'
  $btnRun  = New-Object Windows.Forms.Button; $btnRun.Text="실행"; $btnRun.Dock='Fill'
  $btnOpen = New-Object Windows.Forms.Button; $btnOpen.Text="폴더열기"; $btnOpen.Dock='Fill'

  $pb = New-Object Windows.Forms.ProgressBar; $pb.Dock='Fill'; $pb.Style='Marquee'
  $pb.Visible=$false

  $tb = New-Object Windows.Forms.TextBox; $tb.Multiline=$true; $tb.ScrollBars='Vertical'; $tb.Dock='Fill'

  $btnBest  = New-Object Windows.Forms.Button; $btnBest.Text="베스트"; $btnBest.Dock='Fill'
  $btnWorst = New-Object Windows.Forms.Button; $btnWorst.Text="워스트"; $btnWorst.Dock='Fill'
  $btnStop  = New-Object Windows.Forms.Button; $btnStop.Text="중지";   $btnStop.Dock='Fill'

  $tbl.Controls.Add($cb,0,0); $tbl.SetColumnSpan($cb,1)
  $tbl.Controls.Add($btnScan,1,0)
  $tbl.Controls.Add($btnRun,2,0)
  $tbl.Controls.Add($btnOpen,3,0)
  $tbl.Controls.Add($pb,0,1); $tbl.SetColumnSpan($pb,4)
  $tbl.Controls.Add($tb,0,2); $tbl.SetColumnSpan($tb,4)

  $btns = New-Object Windows.Forms.TableLayoutPanel
  $btns.Dock='Fill'; $btns.ColumnCount=3
  0..2 | % { $btns.ColumnStyles.Add((New-Object Windows.Forms.ColumnStyle([Windows.Forms.SizeType]::Percent,33))) }
  $btns.Controls.Add($btnBest,0,0)
  $btns.Controls.Add($btnWorst,1,0)
  $btns.Controls.Add($btnStop,2,0)
  $tbl.Controls.Add($btns,0,3); $tbl.SetColumnSpan($btns,4)

  $g.Controls.Add($tbl)

  $state = @{
    lastOutDir = $null
  }

  $btnScan.Add_Click({
    $cb.Items.Clear()
    (Get-ModelDirs) | % { [void]$cb.Items.Add($_) }
    if($cb.Items.Count -gt 0){ $cb.SelectedIndex=0 }
  })

  $btnOpen.Add_Click({
    if($state.lastOutDir -and (Test-Path $state.lastOutDir)){ Start-Process explorer $state.lastOutDir }
  })

  $btnBest.Add_Click({
    if($state.lastOutDir -and (Test-Path $state.lastOutDir)){
      $dest = Join-Path $BEST ([IO.Path]::GetFileName($state.lastOutDir))
      Copy-Item $state.lastOutDir $dest -Recurse -Force
      [System.Windows.Forms.MessageBox]::Show("베스트에 복사됨: $dest") | Out-Null
    }
  })
  $btnWorst.Add_Click({
    if($state.lastOutDir -and (Test-Path $state.lastOutDir)){
      $dest = Join-Path $WORST ([IO.Path]::GetFileName($state.lastOutDir))
      Copy-Item $state.lastOutDir $dest -Recurse -Force
      [System.Windows.Forms.MessageBox]::Show("워스트에 복사됨: $dest") | Out-Null
    }
  })

  $runOne = {
    $model = $cb.SelectedItem
    if(-not $model){ return }
    $tb.Clear(); $pb.Visible=$true

    $ts = (Get-Date).ToString("yyyyMMdd_HHmmss")
    $tag = "m$idx"+"_"+$ts
    $outDir = Join-Path $REC $tag
    New-Item -ItemType Directory -Force -Path $outDir | Out-Null
    $state.lastOutDir = $outDir

    $outTxt   = Join-Path $outDir "out.txt"
    $outJsonl = Join-Path $DATA "corpus.jsonl"
    $outStl   = Join-Path $outDir "design.stl"

    $args = @(
      $RUNPY,
      "--model_dir",$model,
      "--device",$cbDev.SelectedItem,
      "--prompt",$txtPrompt.Text,
      "--max_new_tokens",[int]$nudTok.Value,
      "--temperature",[double]$nudT.Value,
      "--top_p",[double]$nudTopP.Value,
      "--top_k",[int]$nudTopK.Value,
      "--out_txt",$outTxt,
      "--out_jsonl",$outJsonl
    ) | % { Q $_ }

    $psi=[Diagnostics.ProcessStartInfo]::new()
    $psi.FileName=$PY; $psi.Arguments=($args -join " "); $psi.UseShellExecute=$false
    $psi.RedirectStandardOutput=$true; $psi.RedirectStandardError=$true; $psi.CreateNoWindow=$true
    $p=[Diagnostics.Process]::new(); $p.StartInfo=$psi
    [void]$p.Start(); $procs["m$idx"]=$p

    while(-not $p.HasExited){
      while(-not $p.StandardOutput.EndOfStream){ $l=$p.StandardOutput.ReadLine(); if($l){ $tb.AppendText($l+"`r`n") } }
      while(-not $p.StandardError.EndOfStream){  $l=$p.StandardError.ReadLine(); if($l){ $tb.AppendText("[ERR] "+$l+"`r`n") } }
      Start-Sleep -Milliseconds 60
    }

    # 3D 더미 STL 생성
    & $PY $STLPY --out_stl $outStl | Out-Null

    $pb.Visible=$false
    Prune-Recent
  }

  $btnRun.Add_Click($runOne)
  $btnStop.Add_Click({
    $key="m$idx"
    if($procs.ContainsKey($key)){
      try{ $procs[$key].Kill(); $procs.Remove($key) }catch{}
    }
    $pb.Visible=$false
  })

  return $g
}

# 메인 레이아웃
$grid = New-Object Windows.Forms.TableLayoutPanel
$grid.Dock='Fill'; $grid.RowCount=2; $grid.ColumnCount=2
0..1 | % { $grid.RowStyles.Add((New-Object Windows.Forms.RowStyle([Windows.Forms.SizeType]::Percent,50))) }
0..1 | % { $grid.ColumnStyles.Add((New-Object Windows.Forms.ColumnStyle([Windows.Forms.SizeType]::Percent,50))) }

$m1 = New-ModelPane 1
$m2 = New-ModelPane 2
$m3 = New-ModelPane 3
$m4 = New-ModelPane 4
$grid.Controls.Add($m1,0,0)
$grid.Controls.Add($m2,1,0)
$grid.Controls.Add($m3,0,1)
$grid.Controls.Add($m4,1,1)

# 상단 버튼 액션
$btnRunAll.Add_Click({ $m1.Controls[0].Controls[2].Controls[1].PerformClick(); $m2.Controls[0].Controls[2].Controls[1].PerformClick(); $m3.Controls[0].Controls[2].Controls[1].PerformClick(); $m4.Controls[0].Controls[2].Controls[1].PerformClick() })
$btnStopAll.Add_Click({
  foreach($k in @($procs.Keys)){ try{ $procs[$k].Kill() }catch{}; $procs.Remove($k) }
})

# 합체
$f.Controls.Add($grid)
$f.Controls.Add($top)
[void]$f.ShowDialog()