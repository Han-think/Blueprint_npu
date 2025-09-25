Param([string]$Manifest = "$(Split-Path $PSScriptRoot -Parent)\config\models.json")
$ErrorActionPreference="Stop"
if(!(Test-Path $Manifest)){ Write-Host "no models.json. skip." ; exit 0 }
$m = Get-Content $Manifest -Raw | ConvertFrom-Json
foreach($it in $m){
  $url=$it.url; $zipName=$it.save_as; $into=Join-Path (Split-Path $PSScriptRoot -Parent) $it.into
  $zipPath = Join-Path (Split-Path $PSScriptRoot -Parent) ("data\models\" + $zipName)
  if(Test-Path $into -PathType Container){ continue }
  Write-Host "downloading $($it.name) ..."
  Invoke-WebRequest -Uri $url -OutFile $zipPath
  if($it.sha256 -and $it.sha256 -ne ""){
    $h = (Get-FileHash $zipPath -Algorithm SHA256).Hash.ToLower()
    if($h -ne $it.sha256.ToLower()){ throw "checksum mismatch for $zipName" }
  }
  New-Item -ItemType Directory -Force -Path $into | Out-Null
  Expand-Archive -Path $zipPath -DestinationPath $into -Force
}
