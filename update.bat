@echo off
echo ================================================
echo  Invoice System - Update
echo ================================================
echo.

echo Step 1 - Stopping app...
taskkill /f /im python.exe >nul 2>&1
timeout /t 2 /nobreak >nul

echo Step 2 - Checking Git...
where git >nul 2>&1
if %errorlevel% neq 0 (
    echo Git not found - attempting to install...
    powershell -NoProfile -ExecutionPolicy Bypass -Command ^
        "$u='https://github.com/git-for-windows/git/releases/download/v2.44.0.windows.1/Git-2.44.0-64-bit.exe';" ^
        "$d='%TEMP%\git_inst.exe';" ^
        "(New-Object System.Net.WebClient).DownloadFile($u,$d);" ^
        "Start-Process $d '/VERYSILENT /NORESTART /NOCANCEL /SP-' -Wait"
    set "PATH=%PATH%;C:\Program Files\Git\cmd"
)

echo Step 2b - Fixing Git folder permissions...
for /f "delims=" %%i in ('cd') do set CURRENT_DIR=%%i
git config --global --add safe.directory "%CURRENT_DIR%" >nul 2>&1
git config --global --add safe.directory C:/InvoicesApp >nul 2>&1
git config --global --add safe.directory D:/InvoicesApp >nul 2>&1

echo Step 3 - Pulling latest update...
cd /d %CURRENT_DIR%
git pull

echo Step 4 - Starting app...
wscript.exe "%CURRENT_DIR%\run.vbs"
echo App is starting - you can close this window.
pause
