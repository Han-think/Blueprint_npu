$ErrorActionPreference="Stop"
$PORT=9035
# 빌드(최종 설계 기본값)
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
  ribs_count    = 8
  base_enable   = $true
  cradles_enable= $true
  drive_z_frac  = 0.20
  pulley_r_engine = 8.0
  pulley_r_motor  = 10.0
  belt_width    = 6.0
  belt_thick    = 1.6
}
$run = Invoke-RestMethod -Method Post "http://127.0.0.1:$PORT/wb/cad/j58_v23" -ContentType application/json -Body ($body | ConvertTo-Json)
# 청사진 열기
$bp  = Invoke-RestMethod "http://127.0.0.1:$PORT/wb/cad/j58_blueprint"
if($bp.ok){ Start-Process "http://127.0.0.1:$PORT/wb/files/$($bp.svg_rel)" }
# 플레이트(R/L)
$R = Invoke-RestMethod -Method Post "http://127.0.0.1:$PORT/wb/cad/j58_v23_plate" -ContentType application/json -Body (@{engine_tag="R"; set="core"; plate_w=220; plate_d=220; place_shaft_on_last=$true; shaft_angle=45; runner_like=$true} | ConvertTo-Json)
$L = Invoke-RestMethod -Method Post "http://127.0.0.1:$PORT/wb/cad/j58_v23_plate" -ContentType application/json -Body (@{engine_tag="L"; set="core"; plate_w=220; plate_d=220; place_shaft_on_last=$true; shaft_angle=45; runner_like=$true} | ConvertTo-Json)
