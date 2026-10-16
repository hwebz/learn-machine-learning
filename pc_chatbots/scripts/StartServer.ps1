<#
.SYNOPSIS
    Khởi động Deep Research Local API Server (FastAPI / Uvicorn).

.DESCRIPTION
    Script tiện ích tự động:
      1. Định vị thư mục gốc pc_chatbots.
      2. Kích hoạt môi trường ảo Python (.venv) nếu có.
      3. Kiểm tra cổng (mặc định 8000) xem có bị xung đột không.
      4. Khởi chạy Uvicorn server tại http://127.0.0.1:8000.

.EXAMPLE
    .\scripts\StartServer.ps1

.EXAMPLE
    .\scripts\StartServer.ps1 -Port 8001 -Reload
#>

[CmdletBinding()]
param(
    [string]$HostAddress = "127.0.0.1",
    [int]$Port = 8000,
    [switch]$Reload,
    [switch]$KillExisting
)

$ErrorActionPreference = "Stop"

if ($HostAddress -like "-*") {
    if ($HostAddress -like "*Reload*") { $Reload = $true }
    if ($HostAddress -like "*KillExisting*") { $KillExisting = $true }
    $HostAddress = "127.0.0.1"
}

# Định vị thư mục gốc pc_chatbots (thư mục cha của thư mục chứa script này)
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir
Set-Location $ProjectRoot

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "  Deep Research Local - Starting API Server" -ForegroundColor Cyan
Write-Host "  Thư mục: $ProjectRoot" -ForegroundColor DarkGray
Write-Host "==========================================================" -ForegroundColor Cyan

# 1. Kiểm tra và kích hoạt virtual environment
$PythonExe = "python"
$VenvPython = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
$VenvActivate = Join-Path $ProjectRoot ".venv\Scripts\Activate.ps1"
if (Test-Path $VenvActivate) {
    Write-Host "[1/3] Activate virtual environment (.venv)..." -ForegroundColor Green
    & $VenvActivate
    if (Test-Path $VenvPython) {
        $PythonExe = $VenvPython
    }
}
else {
    Write-Host "[WARNING] Cannot find $VenvActivate. Using Python from system." -ForegroundColor Yellow
}

# 2. Kiểm tra xung đột cổng
$ExistingConns = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue | Where-Object { $_.OwningProcess -ne 0 }
if ($ExistingConns) {
    $Pids = $ExistingConns | Select-Object -ExpandProperty OwningProcess -Unique
    $shouldKill = $KillExisting -or $Reload
    if (-not $shouldKill) {
        $allPython = $true
        foreach ($p in $Pids) {
            $proc = Get-Process -Id $p -ErrorAction SilentlyContinue
            if (-not $proc -or $proc.ProcessName -notlike "*python*") {
                $allPython = $false
            }
        }
        if ($allPython) {
            $shouldKill = $true
        }
    }

    if ($shouldKill) {
        Write-Host "[KILL] Killing process on port $Port (PID: $($Pids -join ', '))..." -ForegroundColor Yellow
        foreach ($p in $Pids) {
            Stop-Process -Id $p -Force -ErrorAction SilentlyContinue
        }
        Start-Sleep -Seconds 1
    }
    else {
        Write-Host "[ERROR/WARNING] Port $Port is being used by PID: $($Pids -join ', ')" -ForegroundColor Red
        Write-Host "             You can restart the server with the -KillExisting flag to automatically shut down the old process:" -ForegroundColor Yellow
        Write-Host "             .\scripts\StartServer.ps1 -KillExisting`n" -ForegroundColor Yellow
    }
}

# 3. Start Uvicorn
Write-Host "[2/3] Server address: http://$($HostAddress):$Port" -ForegroundColor Green
Write-Host "      Check health: http://$($HostAddress):$Port/health" -ForegroundColor DarkCyan
Write-Host "[3/3] Starting Uvicorn..." -ForegroundColor Green
Write-Host "      (Press Ctrl + C to stop the server)`n" -ForegroundColor DarkGray

$UvicornArgs = @("app.main:app", "--host", $HostAddress, "--port", "$Port")
# Bắt buộc dùng ProactorEventLoop trên Windows để hỗ trợ subprocess cho Playwright browser automation
if ($env:OS -like "*Windows*" -or $IsWindows -or $env:PROCESSOR_ARCHITECTURE) {
    $UvicornArgs += @("--loop", "app.main:proactor_loop_factory")
}

if ($Reload) {
    if ($env:OS -like "*Windows*" -or $IsWindows -or $env:PROCESSOR_ARCHITECTURE) {
        Write-Host "      [Reload Mode - Windows] Running through watchfiles runner to ensure clean Proactor IOCP..." -ForegroundColor DarkCyan
        & $PythonExe -m watchfiles --filter python "`"$PythonExe`" -m uvicorn $($UvicornArgs -join ' ')" app
        exit $LASTEXITCODE
    }
    else {
        $UvicornArgs += "--reload"
    }
}

& $PythonExe -m uvicorn @UvicornArgs
