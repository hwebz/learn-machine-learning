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

# Định vị thư mục gốc pc_chatbots (thư mục cha của thư mục chứa script này)
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir
Set-Location $ProjectRoot

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "  Deep Research Local - Khởi động API Server" -ForegroundColor Cyan
Write-Host "  Thư mục: $ProjectRoot" -ForegroundColor DarkGray
Write-Host "==========================================================" -ForegroundColor Cyan

# 1. Kiểm tra và kích hoạt virtual environment
$VenvActivate = Join-Path $ProjectRoot ".venv\Scripts\Activate.ps1"
if (Test-Path $VenvActivate) {
    Write-Host "[1/3] Kích hoạt virtual environment (.venv)..." -ForegroundColor Green
    & $VenvActivate
} else {
    Write-Host "[CẢNH BÁO] Không tìm thấy $VenvActivate. Sử dụng Python hiện tại của hệ thống." -ForegroundColor Yellow
}

# 2. Kiểm tra xung đột cổng
$ExistingConns = Get-NetTCPConnection -LocalPort $Port -ErrorAction SilentlyContinue
if ($ExistingConns) {
    $Pids = $ExistingConns | Select-Object -ExpandProperty OwningProcess -Unique
    if ($KillExisting) {
        Write-Host "[XỬ LÝ] Tự động giải phóng cổng $Port (PID: $($Pids -join ', '))..." -ForegroundColor Yellow
        foreach ($p in $Pids) {
            Stop-Process -Id $p -Force -ErrorAction SilentlyContinue
        }
        Start-Sleep -Seconds 1
    } else {
        Write-Host "[LỖI/CẢNH BÁO] Cổng $Port đang được sử dụng bởi Process ID: $($Pids -join ', ')" -ForegroundColor Red
        Write-Host "             Bạn có thể chạy lại với cờ -KillExisting để tự động tắt process cũ:" -ForegroundColor Yellow
        Write-Host "             .\scripts\StartServer.ps1 -KillExisting`n" -ForegroundColor Yellow
    }
}

# 3. Khởi động Uvicorn
Write-Host "[2/3] Địa chỉ server: http://$($HostAddress):$Port" -ForegroundColor Green
Write-Host "      Kiểm tra sức khỏe: http://$($HostAddress):$Port/health" -ForegroundColor DarkCyan
Write-Host "[3/3] Bắt đầu chạy Uvicorn..." -ForegroundColor Green
Write-Host "      (Nhấn Ctrl + C để dừng server)`n" -ForegroundColor DarkGray

$UvicornArgs = @("app.main:app", "--host", $HostAddress, "--port", "$Port")
# Bắt buộc dùng ProactorEventLoop trên Windows để hỗ trợ subprocess cho Playwright browser automation
if ($env:OS -like "*Windows*" -or $IsWindows -or $env:PROCESSOR_ARCHITECTURE) {
    $UvicornArgs += @("--loop", "asyncio:ProactorEventLoop")
}
if ($Reload) {
    $UvicornArgs += "--reload"
}

python -m uvicorn @UvicornArgs
