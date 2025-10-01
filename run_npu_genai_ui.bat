@echo off
setlocal
cd /d "%~dp0"
chcp 65001 >NUL
start "" powershell.exe -NoLogo -NoExit -STA -NoProfile -ExecutionPolicy Bypass -File "%~dp0run_ui_wrap.ps1"
exit /b
