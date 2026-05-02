@echo off
:: ============================================================
::  Invoice App Installer — Launcher
::  Double-click this file to install the app
:: ============================================================

:: Request admin rights if not already running as admin
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo Requesting administrator privileges...
    powershell -Command "Start-Process '%~f0' -Verb RunAs"
    exit /b
)

:: Run the PowerShell installer script from same folder
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0install.ps1"

pause
