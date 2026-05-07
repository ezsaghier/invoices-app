# ================================================================
#  Invoice App Installer - PowerShell Script v3
#  - Installs on D:\ if available, falls back to C:\
#  - Uses git clone (not ZIP download)
#  - Installs and configures Git if missing
#  - Writes install_path.txt for multi-user support
#  - Logs everything to install_log.txt
# ================================================================

# -- Config ------------------------------------------------------
$REPO_URL   = "https://github.com/ezsaghier/invoices_app.git"
$PYTHON_URL = "https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe"
$GIT_URL    = "https://github.com/git-for-windows/git/releases/download/v2.44.0.windows.1/Git-2.44.0-64-bit.exe"
$FOLDER_NAME = "InvoicesApp"
$SCRIPT_DIR  = Split-Path -Parent $MyInvocation.MyCommand.Path
$LOG_FILE    = "$SCRIPT_DIR\install_log.txt"

# -- Helpers -----------------------------------------------------

function Log($msg) {
    $ts = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    Add-Content -Path $LOG_FILE -Value "[$ts] $msg" -Encoding UTF8
}

function Title($msg) {
    Write-Host ""
    Write-Host "  $msg" -ForegroundColor Cyan
    Write-Host ("  " + "-" * $msg.Length) -ForegroundColor DarkGray
    Log "=== $msg ==="
}

function OK($msg)   { Write-Host "  OK  $msg" -ForegroundColor Green;  Log "OK: $msg" }
function INFO($msg) { Write-Host "  ->  $msg" -ForegroundColor Yellow; Log "INFO: $msg" }

function FAIL($msg) {
    Write-Host ""
    Write-Host "  FAILED: $msg" -ForegroundColor Red
    Write-Host "  Log: $LOG_FILE" -ForegroundColor White
    Write-Host "  Send this file to your support contact." -ForegroundColor White
    Log "FAILED: $msg"
    Read-Host "  Press Enter to exit"
    exit 1
}

function RefreshPath() {
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" +
                [System.Environment]::GetEnvironmentVariable("Path","User")
    $env:Path += ";C:\Program Files\Git\cmd"
    $env:Path += ";C:\Program Files\Git\bin"
}

function Check-Command($cmd) {
    return [bool](Get-Command $cmd -ErrorAction SilentlyContinue)
}

function Download($url, $dest, $label) {
    INFO "Downloading $label ..."
    try {
        (New-Object System.Net.WebClient).DownloadFile($url, $dest)
        Log "Downloaded: $url"
    } catch {
        FAIL "Could not download $label : $_"
    }
}

# -- Start -------------------------------------------------------

Clear-Host
Write-Host ""
Write-Host "  +----------------------------------------------+" -ForegroundColor Cyan
Write-Host "  |     Invoice Management System - Installer    |" -ForegroundColor Cyan
Write-Host "  +----------------------------------------------+" -ForegroundColor Cyan
Write-Host ""

"" | Set-Content -Path $LOG_FILE -Encoding UTF8
Log "Installation started"
Log "Windows: $([System.Environment]::OSVersion.VersionString)"
Log "Machine: $env:COMPUTERNAME"
Log "User: $env:USERNAME"

# -- Step 1: Choose install location (D: first, fallback C:) -----

Title "Step 1 of 5 - Choosing Install Location"

$APP_DIR = $null

if (Test-Path "D:\") {
    $APP_DIR = "D:\$FOLDER_NAME"
    OK "Drive D: found - will install to $APP_DIR"
    Log "Install location: $APP_DIR (D: drive)"
} else {
    $APP_DIR = "C:\$FOLDER_NAME"
    INFO "Drive D: not found - falling back to C:\"
    OK "Will install to $APP_DIR"
    Log "Install location: $APP_DIR (C: drive - D: not found)"
}

# Clean up failed previous install if folder exists without .git
if ((Test-Path $APP_DIR) -and (-not (Test-Path "$APP_DIR\.git"))) {
    INFO "Removing incomplete previous installation..."
    Remove-Item -Recurse -Force $APP_DIR
    Log "Removed incomplete folder: $APP_DIR"
}

# -- Step 2: Python ----------------------------------------------

Title "Step 2 of 5 - Python"

$pythonOK = $false
try {
    $pyVer = & python --version 2>&1
    if ($pyVer -match "Python 3\.(\d+)" -and [int]$Matches[1] -ge 9) {
        OK "Python already installed: $pyVer"
        Log "Python: $pyVer"
        $pythonOK = $true
    }
} catch { }

if (-not $pythonOK) {
    $localPy = Get-ChildItem -Path $SCRIPT_DIR -Filter "python-*.exe" -ErrorAction SilentlyContinue |
               Select-Object -First 1
    $pyInst  = if ($localPy) { INFO "Using local Python installer"; $localPy.FullName }
               else { $d = "$env:TEMP\python_installer.exe"; Download $PYTHON_URL $d "Python 3.11"; $d }

    INFO "Installing Python..."
    $p = Start-Process -FilePath $pyInst `
         -ArgumentList "/quiet InstallAllUsers=0 PrependPath=1 Include_pip=1" `
         -Wait -PassThru
    if ($p.ExitCode -ne 0) { FAIL "Python install failed (code $($p.ExitCode))" }
    RefreshPath
    OK "Python installed"
    Log "Python installed"
}

# -- Step 3: Git -------------------------------------------------

Title "Step 3 of 5 - Git"

RefreshPath
$gitOK = Check-Command "git"

if ($gitOK) {
    $gitVer = & git --version 2>&1
    OK "Git already installed: $gitVer"
    Log "Git: $gitVer"
} else {
    INFO "Git not found - installing..."
    $localGit = Get-ChildItem -Path $SCRIPT_DIR -Filter "Git-*.exe" -ErrorAction SilentlyContinue |
                Select-Object -First 1
    $gitInst  = if ($localGit) { INFO "Using local Git installer"; $localGit.FullName }
                else { $d = "$env:TEMP\git_installer.exe"; Download $GIT_URL $d "Git"; $d }

    INFO "Installing Git (silent)..."
    $p = Start-Process -FilePath $gitInst `
         -ArgumentList "/VERYSILENT /NORESTART /NOCANCEL /SP- /COMPONENTS=icons,ext\reg\shellhere,assoc,assoc_sh" `
         -Wait -PassThru
    if ($p.ExitCode -ne 0) { FAIL "Git install failed (code $($p.ExitCode))" }
    RefreshPath
    OK "Git installed"
    Log "Git installed"
}

# Configure Git (required for git pull to work properly)
INFO "Configuring Git..."
try {
    $currentEmail = & git config --global user.email 2>&1
    if (-not $currentEmail) {
        & git config --global user.email "invoiceapp@local.device" 2>&1 | Out-Null
        & git config --global user.name  "Invoice App User"         2>&1 | Out-Null
        Log "Git configured with default identity"
    } else {
        Log "Git already configured: $currentEmail"
    }
    & git config --global core.autocrlf false 2>&1 | Out-Null
    & git config --global pull.rebase false    2>&1 | Out-Null
    OK "Git configured"
} catch {
    Log "Git config warning (non-fatal): $_"
}

# -- Step 4: Clone App -------------------------------------------

Title "Step 4 of 5 - Downloading App"

if (Test-Path "$APP_DIR\.git") {
    INFO "App already installed - updating..."
    Set-Location $APP_DIR
    $result = & git pull 2>&1
    Log "git pull: $result"
    OK "App updated"
} else {
    INFO "Cloning from GitHub..."
    $result = & git clone $REPO_URL $APP_DIR 2>&1
    Log "git clone: $result"
    if (-not (Test-Path "$APP_DIR\app.py")) {
        FAIL "Clone failed - app.py not found in $APP_DIR"
    }
    OK "App downloaded to $APP_DIR"
}

# Write install_path.txt so all user accounts find the same DB
$pathFile = "$APP_DIR\install_path.txt"
Set-Content -Path $pathFile -Value $APP_DIR -Encoding UTF8
OK "Install path saved: $pathFile"
Log "install_path.txt written: $APP_DIR"

# Fix Git ownership issue - add safe.directory for all users
INFO "Configuring Git safe directory..."
$safePath = $APP_DIR.Replace('\', '/')
& git config --global --add safe.directory $safePath 2>&1 | Out-Null
& git config --global --add safe.directory C:/InvoicesApp 2>&1 | Out-Null
& git config --global --add safe.directory D:/InvoicesApp 2>&1 | Out-Null
OK "Git safe directory configured"
Log "Git safe.directory set for: $safePath"

# -- Step 5: Flask + Shortcuts -----------------------------------

Title "Step 5 of 5 - Flask and Shortcuts"

INFO "Installing Flask..."
$result = & python -m pip install flask --quiet 2>&1
Log "pip: $result"
if ($LASTEXITCODE -ne 0) { FAIL "Flask install failed" }
OK "Flask installed"

# run.bat (debug only - visible terminal - machine specific, gitignored)
$runBat = "$APP_DIR\run.bat"
$rb  = "@echo off`r`n"
$rb += "set INVOICES_APP_DIR=$APP_DIR`r`n"
$rb += "cd /d $APP_DIR`r`n"
$rb += "echo Starting Invoice System...`r`n"
$rb += "python app.py`r`n"
$rb += "pause`r`n"
[System.IO.File]::WriteAllText($runBat, $rb)
OK "Created run.bat (debug launcher)"

# Note: run.vbs and update.bat are NOT generated here.
# They are provided by git clone from the repo and contain
# dynamic install_path.txt reading - do not overwrite them.

# Desktop shortcut (works for ALL user accounts on this machine)
$desktopPath  = [System.Environment]::GetFolderPath("CommonDesktopDirectory")
if (-not $desktopPath) {
    $desktopPath = [System.Environment]::GetFolderPath("Desktop")
}
$shortcutPath = "$desktopPath\InvoiceSystem.lnk"
$shell        = New-Object -ComObject WScript.Shell
$shortcut     = $shell.CreateShortcut($shortcutPath)
$shortcut.TargetPath       = "wscript.exe"
$shortcut.Arguments        = "`"$APP_DIR\run.vbs`""
$shortcut.WorkingDirectory = $APP_DIR
$shortcut.Description      = "Invoice Management System"
$shortcut.IconLocation     = "shell32.dll,13"
$shortcut.Save()
OK "Desktop shortcut created (all users): $shortcutPath"
Log "Shortcut: $shortcutPath"

# -- Done --------------------------------------------------------

Write-Host ""
Write-Host "  +----------------------------------------------+" -ForegroundColor Green
Write-Host "  |        Installation Complete!                |" -ForegroundColor Green
Write-Host "  +----------------------------------------------+" -ForegroundColor Green
Write-Host ""
Write-Host "  Installed at : $APP_DIR" -ForegroundColor White
Write-Host "  Start app    : double-click InvoiceSystem on Desktop" -ForegroundColor Yellow
Write-Host "  Updates      : double-click update.bat in $APP_DIR" -ForegroundColor Yellow
Write-Host "  Log          : $LOG_FILE" -ForegroundColor DarkGray
Write-Host ""
Log "Installation completed: $APP_DIR"

$launch = Read-Host "  Launch the app now? (y/n)"
if ($launch -eq "y" -or $launch -eq "Y" -or $launch -eq "") {
    Log "Launching app..."
    Start-Process "wscript.exe" -ArgumentList "`"$APP_DIR\run.vbs`""
    Start-Sleep -Seconds 2
    Start-Process "http://127.0.0.1:5001"
}