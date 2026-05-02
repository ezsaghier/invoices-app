# ================================================================
#  Invoice App Installer — PowerShell Script
#  Works fully offline if Python installer is on the USB
#  Logs everything to install_log.txt
# ================================================================

$ErrorActionPreference = "Stop"

# ── Config ──────────────────────────────────────────────────────
$APP_DIR     = "D:\InvoicesApp"
$REPO_URL    = "https://github.com/YOUR_USERNAME/invoices-app.git"
$LOG_FILE    = "$APP_DIR\install_log.txt"
$PYTHON_URL  = "https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe"
$GIT_URL     = "https://github.com/git-for-windows/git/releases/download/v2.44.0.windows.1/Git-2.44.0-64-bit.exe"
$PYTHON_INSTALLER = "$env:TEMP\python_installer.exe"
$GIT_INSTALLER    = "$env:TEMP\git_installer.exe"

# ── Helpers ──────────────────────────────────────────────────────

function Log($msg) {
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $line = "[$timestamp] $msg"
    Add-Content -Path $LOG_FILE -Value $line -Encoding UTF8
}

function Title($msg) {
    Write-Host ""
    Write-Host "  $msg" -ForegroundColor Cyan
    Write-Host ("  " + "─" * ($msg.Length)) -ForegroundColor DarkGray
    Log "=== $msg ==="
}

function OK($msg) {
    Write-Host "  ✓  $msg" -ForegroundColor Green
    Log "OK: $msg"
}

function INFO($msg) {
    Write-Host "  →  $msg" -ForegroundColor Yellow
    Log "INFO: $msg"
}

function ERR($msg) {
    Write-Host ""
    Write-Host "  ✗  ERROR: $msg" -ForegroundColor Red
    Write-Host ""
    Write-Host "  The installation log is saved at:" -ForegroundColor White
    Write-Host "  $LOG_FILE" -ForegroundColor White
    Write-Host ""
    Write-Host "  Please send this file to your support contact." -ForegroundColor White
    Log "ERROR: $msg"
}

function Download($url, $dest, $label) {
    INFO "Downloading $label ..."
    try {
        $wc = New-Object System.Net.WebClient
        $wc.DownloadFile($url, $dest)
        OK "Downloaded $label"
        Log "Downloaded: $url -> $dest"
    } catch {
        throw "Failed to download $label : $_"
    }
}

function Check-Command($cmd) {
    return [bool](Get-Command $cmd -ErrorAction SilentlyContinue)
}

# ── Start ────────────────────────────────────────────────────────

Clear-Host
Write-Host ""
Write-Host "  ╔══════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "  ║     نظام إدارة الفواتير — المثبّت           ║" -ForegroundColor Cyan
Write-Host "  ║     Invoice Management System Installer      ║" -ForegroundColor Cyan
Write-Host "  ╚══════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

# Create app directory and start log
if (-not (Test-Path $APP_DIR)) {
    New-Item -ItemType Directory -Path $APP_DIR -Force | Out-Null
}
"" | Set-Content -Path $LOG_FILE -Encoding UTF8
Log "Installation started"
Log "Windows version: $([System.Environment]::OSVersion.VersionString)"
Log "Machine: $env:COMPUTERNAME"
Log "User: $env:USERNAME"
Log "App directory: $APP_DIR"

# ── Step 1: Check / Install Python ───────────────────────────────

Title "Step 1 of 5 — Python"

$pythonOK = $false
try {
    $pyVersion = & python --version 2>&1
    if ($pyVersion -match "Python 3\.(\d+)") {
        $minor = [int]$Matches[1]
        if ($minor -ge 9) {
            OK "Python already installed: $pyVersion"
            Log "Python found: $pyVersion"
            $pythonOK = $true
        } else {
            INFO "Python version too old ($pyVersion) — installing newer version"
        }
    }
} catch {
    INFO "Python not found — will install"
}

if (-not $pythonOK) {
    # Check if installer is on USB (same folder as this script)
    $scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
    $localInstaller = Get-ChildItem -Path $scriptDir -Filter "python-*.exe" | Select-Object -First 1

    if ($localInstaller) {
        INFO "Found Python installer on USB: $($localInstaller.Name)"
        $PYTHON_INSTALLER = $localInstaller.FullName
    } else {
        Download $PYTHON_URL $PYTHON_INSTALLER "Python 3.11"
    }

    INFO "Installing Python (this may take a minute)..."
    $args = "/quiet InstallAllUsers=0 PrependPath=1 Include_pip=1"
    $proc = Start-Process -FilePath $PYTHON_INSTALLER -ArgumentList $args -Wait -PassThru
    if ($proc.ExitCode -ne 0) {
        ERR "Python installation failed (exit code $($proc.ExitCode))"
        Read-Host "Press Enter to exit"
        exit 1
    }

    # Refresh PATH
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" +
                [System.Environment]::GetEnvironmentVariable("Path","User")

    OK "Python installed successfully"
    Log "Python installed"
}

# ── Step 2: Check / Install Git ──────────────────────────────────

Title "Step 2 of 5 — Git"

$gitOK = Check-Command "git"

if ($gitOK) {
    $gitVersion = & git --version 2>&1
    OK "Git already installed: $gitVersion"
    Log "Git found: $gitVersion"
} else {
    INFO "Git not found — will install"

    $scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
    $localGit = Get-ChildItem -Path $scriptDir -Filter "Git-*.exe" | Select-Object -First 1

    if ($localGit) {
        INFO "Found Git installer on USB: $($localGit.Name)"
        $GIT_INSTALLER = $localGit.FullName
    } else {
        Download $GIT_URL $GIT_INSTALLER "Git"
    }

    INFO "Installing Git (this may take a minute)..."
    $args = "/VERYSILENT /NORESTART /NOCANCEL /SP- /CLOSEAPPLICATIONS /RESTARTAPPLICATIONS /COMPONENTS=icons,ext\reg\shellhere,assoc,assoc_sh"
    $proc = Start-Process -FilePath $GIT_INSTALLER -ArgumentList $args -Wait -PassThru
    if ($proc.ExitCode -ne 0) {
        ERR "Git installation failed (exit code $($proc.ExitCode))"
        Read-Host "Press Enter to exit"
        exit 1
    }

    # Refresh PATH
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" +
                [System.Environment]::GetEnvironmentVariable("Path","User")
    $env:Path += ";C:\Program Files\Git\cmd"

    OK "Git installed successfully"
    Log "Git installed"
}

# ── Step 3: Clone or Update the app ──────────────────────────────

Title "Step 3 of 5 — Downloading the App"

if (Test-Path "$APP_DIR\.git") {
    INFO "App already exists — updating to latest version..."
    Set-Location $APP_DIR
    try {
        & git pull 2>&1 | ForEach-Object { Log "git pull: $_" }
        OK "App updated to latest version"
    } catch {
        ERR "Failed to update app: $_"
        Read-Host "Press Enter to exit"
        exit 1
    }
} else {
    INFO "Downloading app files from GitHub..."
    try {
        & git clone $REPO_URL $APP_DIR 2>&1 | ForEach-Object {
            Log "git clone: $_"
            Write-Host "  →  $_" -ForegroundColor DarkGray
        }
        OK "App downloaded successfully"
    } catch {
        ERR "Failed to download app: $_"
        Read-Host "Press Enter to exit"
        exit 1
    }
}

# ── Step 4: Install Python packages ──────────────────────────────

Title "Step 4 of 5 — Installing Required Packages"

Set-Location $APP_DIR

# Check if wheels folder exists (offline install from USB)
$wheelsDir = Join-Path (Split-Path -Parent $MyInvocation.MyCommand.Path) "wheels"

if (Test-Path $wheelsDir) {
    INFO "Installing packages from USB (offline mode)..."
    try {
        & python -m pip install --no-index --find-links="$wheelsDir" flask 2>&1 |
            ForEach-Object { Log "pip: $_" }
        OK "Packages installed from USB"
    } catch {
        ERR "Failed to install packages from USB: $_"
        Read-Host "Press Enter to exit"
        exit 1
    }
} else {
    INFO "Installing packages from internet..."
    try {
        & python -m pip install flask --quiet 2>&1 |
            ForEach-Object { Log "pip: $_" }
        OK "Packages installed"
    } catch {
        ERR "Failed to install packages: $_"
        Read-Host "Press Enter to exit"
        exit 1
    }
}

# ── Step 5: Create desktop shortcut ──────────────────────────────

Title "Step 5 of 5 — Creating Desktop Shortcut"

# run.bat
$runBat = "$APP_DIR\run.bat"
$runContent = "@echo off" + "`r`n"
$runContent += "cd /d D:\InvoicesApp" + "`r`n"
$runContent += "echo Starting Invoice System..." + "`r`n"
$runContent += "python app.py" + "`r`n"
$runContent += "pause" + "`r`n"
[System.IO.File]::WriteAllText($runBat, $runContent)
OK "Created run.bat"

# update.bat
$updateBat = "$APP_DIR\update.bat"
$updateContent = "@echo off" + "`r`n"
$updateContent += "echo Stopping app if running..." + "`r`n"
$updateContent += "taskkill /f /im python.exe >nul 2>&1" + "`r`n"
$updateContent += "cd /d D:\InvoicesApp" + "`r`n"
$updateContent += "echo Downloading latest updates..." + "`r`n"
$updateContent += "git pull" + "`r`n"
$updateContent += "echo." + "`r`n"
$updateContent += "echo Update complete. Starting app..." + "`r`n"
$updateContent += "python app.py" + "`r`n"
$updateContent += "pause" + "`r`n"
[System.IO.File]::WriteAllText($updateBat, $updateContent)
OK "Created update.bat"

# Desktop shortcut for run.bat
$desktopPath = [System.Environment]::GetFolderPath("Desktop")
$shortcutPath = "$desktopPath\نظام الفواتير.lnk"

$shell = New-Object -ComObject WScript.Shell
$shortcut = $shell.CreateShortcut($shortcutPath)
$shortcut.TargetPath  = $runBat
$shortcut.WorkingDirectory = $APP_DIR
$shortcut.Description = "Invoice Management System"
$shortcut.IconLocation = "shell32.dll,13"
$shortcut.Save()
OK "Desktop shortcut created"
Log "Desktop shortcut created: $shortcutPath"

# ── Done ─────────────────────────────────────────────────────────

Write-Host ""
Write-Host "  ╔══════════════════════════════════════════════╗" -ForegroundColor Green
Write-Host "  ║        Installation Complete!  ✓             ║" -ForegroundColor Green
Write-Host "  ╚══════════════════════════════════════════════╝" -ForegroundColor Green
Write-Host ""
Write-Host "  The app is installed at: $APP_DIR" -ForegroundColor White
Write-Host ""
Write-Host "  To start the app:" -ForegroundColor White
Write-Host "  → Double-click  'نظام الفواتير'  on the Desktop" -ForegroundColor Yellow
Write-Host ""
Write-Host "  To update the app in the future:" -ForegroundColor White
Write-Host "  → Double-click  update.bat  in $APP_DIR" -ForegroundColor Yellow
Write-Host ""
Write-Host "  Installation log saved at:" -ForegroundColor White
Write-Host "  $LOG_FILE" -ForegroundColor DarkGray
Write-Host ""

Log "Installation completed successfully"

# Ask to launch now
$launch = Read-Host "  Launch the app now? (y/n)"
if ($launch -eq "y" -or $launch -eq "Y" -or $launch -eq "") {
    Log "Launching app..."
    Start-Process -FilePath $runBat
}