# ================================================================
#  Invoice App Installer - PowerShell Script
#  Downloads app as ZIP from GitHub - no Git required
#  Logs everything to install_log.txt (same folder as this script)
# ================================================================

# -- Config ------------------------------------------------------
$APP_DIR    = "D:\InvoicesApp"
$GITHUB_ZIP = "https://github.com/ezsaghier/invoices-app/archive/refs/heads/main.zip"
$PYTHON_URL = "https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe"
$SCRIPT_DIR = Split-Path -Parent $MyInvocation.MyCommand.Path
$LOG_FILE   = "$SCRIPT_DIR\install_log.txt"
$ZIP_DEST   = "$env:TEMP\invoices_app.zip"
$EXTRACT_TO = "$env:TEMP\invoices_extract"

# -- Helpers -----------------------------------------------------

function Log($msg) {
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $line = "[$timestamp] $msg"
    Add-Content -Path $LOG_FILE -Value $line -Encoding UTF8
}

function Title($msg) {
    Write-Host ""
    Write-Host "  $msg" -ForegroundColor Cyan
    Write-Host ("  " + "-" * ($msg.Length)) -ForegroundColor DarkGray
    Log "=== $msg ==="
}

function OK($msg) {
    Write-Host "  OK  $msg" -ForegroundColor Green
    Log "OK: $msg"
}

function INFO($msg) {
    Write-Host "  ->  $msg" -ForegroundColor Yellow
    Log "INFO: $msg"
}

function FAIL($msg) {
    Write-Host ""
    Write-Host "  FAILED: $msg" -ForegroundColor Red
    Write-Host ""
    Write-Host "  Log saved at: $LOG_FILE" -ForegroundColor White
    Write-Host "  Please send this file to your support contact." -ForegroundColor White
    Log "FAILED: $msg"
    Read-Host "  Press Enter to exit"
    exit 1
}

# -- Start -------------------------------------------------------

Clear-Host
Write-Host ""
Write-Host "  +----------------------------------------------+" -ForegroundColor Cyan
Write-Host "  |     Invoice Management System - Installer    |" -ForegroundColor Cyan
Write-Host "  +----------------------------------------------+" -ForegroundColor Cyan
Write-Host ""

# Start log
"" | Set-Content -Path $LOG_FILE -Encoding UTF8
Log "Installation started"
Log "Windows: $([System.Environment]::OSVersion.VersionString)"
Log "Machine: $env:COMPUTERNAME"
Log "User: $env:USERNAME"
Log "App dir: $APP_DIR"

# -- Step 1: Python ----------------------------------------------

Title "Step 1 of 4 - Python"

$pythonOK = $false
try {
    $pyVer = & python --version 2>&1
    if ($pyVer -match "Python 3\.(\d+)") {
        if ([int]$Matches[1] -ge 9) {
            OK "Python already installed: $pyVer"
            Log "Python found: $pyVer"
            $pythonOK = $true
        }
    }
} catch { }

if (-not $pythonOK) {
    # Check for local installer in same folder as this script
    $localPy = Get-ChildItem -Path $SCRIPT_DIR -Filter "python-*.exe" -ErrorAction SilentlyContinue |
               Select-Object -First 1

    $pyInstaller = if ($localPy) {
        INFO "Found Python installer: $($localPy.Name)"
        $localPy.FullName
    } else {
        INFO "Downloading Python 3.11..."
        $dest = "$env:TEMP\python_installer.exe"
        try {
            (New-Object System.Net.WebClient).DownloadFile($PYTHON_URL, $dest)
            Log "Downloaded Python: $PYTHON_URL"
        } catch {
            FAIL "Could not download Python: $_"
        }
        $dest
    }

    INFO "Installing Python..."
    $proc = Start-Process -FilePath $pyInstaller `
            -ArgumentList "/quiet InstallAllUsers=0 PrependPath=1 Include_pip=1" `
            -Wait -PassThru
    if ($proc.ExitCode -ne 0) { FAIL "Python install failed (code $($proc.ExitCode))" }

    $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" +
                [System.Environment]::GetEnvironmentVariable("Path","User")
    OK "Python installed"
    Log "Python installed"
}

# -- Step 2: Flask -----------------------------------------------

Title "Step 2 of 4 - Installing Flask"

# Check for offline wheels folder
$wheelsDir = Join-Path $SCRIPT_DIR "wheels"

if (Test-Path $wheelsDir) {
    INFO "Installing Flask from USB (offline)..."
    $result = & python -m pip install --no-index --find-links="$wheelsDir" flask 2>&1
    Log "pip (offline): $result"
} else {
    INFO "Installing Flask from internet..."
    $result = & python -m pip install flask --quiet 2>&1
    Log "pip: $result"
}

if ($LASTEXITCODE -ne 0) { FAIL "Flask install failed: $result" }
OK "Flask installed"

# -- Step 3: Download App ----------------------------------------

Title "Step 3 of 4 - Downloading the App"

# Clean up previous install if needed
if (Test-Path $APP_DIR) {
    INFO "Removing previous installation..."
    Remove-Item -Recurse -Force $APP_DIR
    Log "Removed: $APP_DIR"
}

# Clean up previous temp extract
if (Test-Path $EXTRACT_TO) {
    Remove-Item -Recurse -Force $EXTRACT_TO
}

INFO "Downloading app from GitHub..."
try {
    (New-Object System.Net.WebClient).DownloadFile($GITHUB_ZIP, $ZIP_DEST)
    Log "Downloaded ZIP: $GITHUB_ZIP"
} catch {
    FAIL "Could not download app: $_"
}
OK "Download complete"

INFO "Extracting files..."
try {
    Expand-Archive -Path $ZIP_DEST -DestinationPath $EXTRACT_TO -Force
    Log "Extracted to: $EXTRACT_TO"
} catch {
    FAIL "Could not extract ZIP: $_"
}

# GitHub ZIP contains a subfolder named "invoices-app-main" - move its contents to APP_DIR
$extracted = Get-ChildItem -Path $EXTRACT_TO | Select-Object -First 1
if (-not $extracted) { FAIL "Extracted folder is empty" }

Move-Item -Path $extracted.FullName -Destination $APP_DIR
Log "Moved app to: $APP_DIR"

# Clean up temp files
Remove-Item -Force $ZIP_DEST -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force $EXTRACT_TO -ErrorAction SilentlyContinue

OK "App files installed to $APP_DIR"

# -- Step 4: Shortcuts -------------------------------------------

Title "Step 4 of 4 - Creating Shortcuts"

# run.bat - kept for debugging purposes
$runBat = "$APP_DIR\run.bat"
$rc  = "@echo off`r`n"
$rc += "cd /d D:\InvoicesApp`r`n"
$rc += "echo Starting Invoice System...`r`n"
$rc += "python app.py`r`n"
$rc += "pause`r`n"
[System.IO.File]::WriteAllText($runBat, $rc)
OK "Created run.bat"

# run.vbs - silent launcher (no terminal window)
$runVbs = "$APP_DIR\run.vbs"
$vbs  = "' Invoice System - Silent Launcher`r`n"
$vbs += "Set objShell = CreateObject(`"WScript.Shell`")`r`n"
$vbs += "objShell.CurrentDirectory = `"D:\InvoicesApp`"`r`n"
$vbs += "objShell.Run `"python app.py`", 0, False`r`n"
[System.IO.File]::WriteAllText($runVbs, $vbs)
OK "Created run.vbs"

# update.bat - stops app, downloads fresh ZIP, preserves database, restarts
$updateBat = "$APP_DIR\update.bat"
$uc  = "@echo off`r`n"
$uc += "echo ================================================`r`n"
$uc += "echo  Invoice System - Update`r`n"
$uc += "echo ================================================`r`n"
$uc += "echo.`r`n"
$uc += "echo Step 1 - Stopping the app...`r`n"
$uc += "taskkill /f /im python.exe >nul 2>&1`r`n"
$uc += "timeout /t 2 /nobreak >nul`r`n"
$uc += "echo Step 2 - Downloading latest update...`r`n"
$uc += "powershell -NoProfile -ExecutionPolicy Bypass -Command `""
$uc += "(New-Object System.Net.WebClient).DownloadFile('$GITHUB_ZIP', '%TEMP%\inv_update.zip'); "
$uc += "Expand-Archive '%TEMP%\inv_update.zip' '%TEMP%\inv_update' -Force; "
$uc += "`$src = (Get-ChildItem '%TEMP%\inv_update' | Select-Object -First 1).FullName; "
$uc += "Get-ChildItem `"`$src`" | Where-Object { `$_.Name -notin @('invoices.db','backups') } | "
$uc += "ForEach-Object { Copy-Item `$_.FullName 'D:\InvoicesApp\' -Recurse -Force }; "
$uc += "Remove-Item '%TEMP%\inv_update.zip' -Force; "
$uc += "Remove-Item '%TEMP%\inv_update' -Recurse -Force`"" + "`r`n"
$uc += "echo Step 3 - Starting the app...`r`n"
$uc += "cd /d D:\InvoicesApp`r`n"
$uc += "python app.py`r`n"
$uc += "pause`r`n"
[System.IO.File]::WriteAllText($updateBat, $uc)
OK "Created update.bat"

# Desktop shortcut pointing to silent VBS launcher
$desktopPath  = [System.Environment]::GetFolderPath("Desktop")
$shortcutPath = "$desktopPath\InvoiceSystem.lnk"
$shell        = New-Object -ComObject WScript.Shell
$shortcut     = $shell.CreateShortcut($shortcutPath)
$shortcut.TargetPath       = "wscript.exe"
$shortcut.Arguments        = "`"$APP_DIR\run.vbs`""
$shortcut.WorkingDirectory = $APP_DIR
$shortcut.Description      = "Invoice Management System"
$shortcut.IconLocation     = "shell32.dll,13"
$shortcut.Save()
OK "Desktop shortcut created: InvoiceSystem"
Log "Shortcut: $shortcutPath"

# -- Done --------------------------------------------------------

Write-Host ""
Write-Host "  +----------------------------------------------+" -ForegroundColor Green
Write-Host "  |        Installation Complete!                |" -ForegroundColor Green
Write-Host "  +----------------------------------------------+" -ForegroundColor Green
Write-Host ""
Write-Host "  App installed at : $APP_DIR" -ForegroundColor White
Write-Host "  Start the app    : double-click InvoiceSystem on Desktop" -ForegroundColor Yellow
Write-Host "  Future updates   : double-click update.bat in $APP_DIR" -ForegroundColor Yellow
Write-Host "  Install log      : $LOG_FILE" -ForegroundColor DarkGray
Write-Host ""
Log "Installation completed successfully"

$launch = Read-Host "  Launch the app now? (y/n)"
if ($launch -eq "y" -or $launch -eq "Y" -or $launch -eq "") {
    Log "Launching app..."
    Start-Process -FilePath $runBat
}
