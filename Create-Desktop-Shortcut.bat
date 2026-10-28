@echo off
setlocal
cd /d "%~dp0"

echo ========================================================
echo       CleannerAgent - Desktop Shortcut Creator
echo ========================================================
echo.

set "TARGET_EXE=%~dp0dist\CleannerAgent\CleannerAgent.exe"
if not exist "%TARGET_EXE%" (
    set "TARGET_EXE=%~dp0dist\AIPCCleanupAgent\AIPCCleanupAgent.exe"
)

if not exist "%TARGET_EXE%" (
    echo [!] Target executable not found.
    echo Please run the build script or use the installer first.
    pause
    exit /b 1
)

echo [*] Creating Desktop shortcut to:
echo     %TARGET_EXE%
echo.

set "ICON_PATH=%~dp0icon.ico"
if not exist "%ICON_PATH%" (
    set "ICON_PATH=%~dp0assets\icon.ico"
)

powershell -NoProfile -Command ^
  "$WshShell = New-Object -ComObject WScript.Shell; " ^
  "$Shortcut = $WshShell.CreateShortcut([Environment]::GetFolderPath('Desktop') + '\CleannerAgent.lnk'); " ^
  "$Shortcut.TargetPath = '%TARGET_EXE%'; " ^
  "$Shortcut.WorkingDirectory = (Split-Path '%TARGET_EXE%'); " ^
  "$Shortcut.IconLocation = '%ICON_PATH%'; " ^
  "$Shortcut.Description = 'CleannerAgent - Local AI PC Maintenance & Storage Optimizer'; " ^
  "$Shortcut.Save(); " ^
  "Write-Host '[+] Successfully created Desktop shortcut: CleannerAgent' -ForegroundColor Green"

powershell -NoProfile -Command ^
  "$WshShell = New-Object -ComObject WScript.Shell; " ^
  "$StartDir = [Environment]::GetFolderPath('ApplicationData') + '\Microsoft\Windows\Start Menu\Programs'; " ^
  "if (!(Test-Path $StartDir)) { New-Item -ItemType Directory -Path $StartDir -Force | Out-Null }; " ^
  "$Shortcut = $WshShell.CreateShortcut($StartDir + '\CleannerAgent.lnk'); " ^
  "$Shortcut.TargetPath = '%TARGET_EXE%'; " ^
  "$Shortcut.WorkingDirectory = (Split-Path '%TARGET_EXE%'); " ^
  "$Shortcut.IconLocation = '%ICON_PATH%'; " ^
  "$Shortcut.Description = 'CleannerAgent - Local AI PC Maintenance & Storage Optimizer'; " ^
  "$Shortcut.Save(); " ^
  "Write-Host '[+] Successfully created Start Menu shortcut: CleannerAgent' -ForegroundColor Green"

echo.
echo ========================================================
echo [DONE] You can now launch CleannerAgent directly 
echo        from your Desktop or Start Menu!
echo ========================================================
echo.
pause
