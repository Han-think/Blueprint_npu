$ErrorActionPreference="Stop"
$PORT=9035

for($i=0;$i -lt 30;$i++){
  try{ Invoke-RestMethod "http://127.0.0.1:$PORT/health" -TimeoutSec 1 | Out-Null; break } catch { Start-Sleep -s 1 }
}

$body = @{
  both_sides    = $true
  twin_layout   = $true
  engine_cc     = 120
  L_total       = 300
  R_casing      = 30
  eps           = 12.0
  N_fan         = 14
  N_comp        = 16
  N_turb        = 18
  ribs_enable   = $true
  ribs_count    = 6
  base_enable   = $false
  cradles_enable= $false
  drive_z_frac  = 0.20
} | ConvertTo-Json

$run = Invoke-RestMethod -Method Post "http://127.0.0.1:$PORT/wb/cad/j58_v23" -ContentType application/json -Body $body
$bp  = Invoke-RestMethod "http://127.0.0.1:$PORT/wb/cad/j58_blueprint"
if($bp.ok -and $bp.svg_rel){ Start-Process "http://127.0.0.1:$PORT/wb/files/$($bp.svg_rel)" }
"OK: run_dir = $($run.out_dir)"
