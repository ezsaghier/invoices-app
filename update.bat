@echo off
echo ================================================
echo  Invoice System - Update
echo ================================================
echo.
echo Step 1 - Stopping the app...
taskkill /f /im python.exe >nul 2>&1
timeout /t 2 /nobreak >nul
echo Step 2 - Downloading latest update...
cd /d D:\InvoicesApp
git pull
echo Step 3 - Starting the app...
wscript.exe "D:\InvoicesApp\run.vbs"
echo App is starting in the background...
echo You can close this window.
pause
