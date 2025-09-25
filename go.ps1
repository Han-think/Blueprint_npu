$ErrorActionPreference="Stop"
powershell -ExecutionPolicy Bypass -File .\scripts\run_server.ps1
powershell -ExecutionPolicy Bypass -File .\scripts\build_all.ps1
