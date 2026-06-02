<#
.SYNOPSIS
  一键在本机打开多个终端窗口，启动后端、ASR、声纹情感、前端（可选）。
#>
[CmdletBinding()]
param(
    [switch]$NoFrontend,
    [switch]$NoVprSer
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $RepoRoot

# 定义Python路径
$Py = Join-Path $RepoRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $Py)) {
    Write-Host "错误：未找到Python环境！路径：$Py" -ForegroundColor Red
    Write-Host "请先在仓库根目录执行：python -m venv .venv" -ForegroundColor Red
    exit 1
}

# 启动新窗口函数
function Start-DevWindow {
    param([string]$Command)
    Start-Process powershell.exe -ArgumentList "-NoExit", "-Command", $Command
}

# 中文提示
Write-Host "仓库根目录：$RepoRoot" -ForegroundColor Cyan
Write-Host "即将打开新窗口启动所有服务（关闭窗口即停止服务）" -ForegroundColor Cyan

# 启动后端服务
Write-Host "启动后端服务（端口8000）..." -ForegroundColor Cyan
Start-DevWindow "Set-Location '$RepoRoot\backend'; & '$Py' run_server.py"

# 启动ASR服务
Write-Host "启动ASR服务（端口8090）..." -ForegroundColor Cyan
Start-DevWindow "Set-Location '$RepoRoot\ai-asr'; & '$Py' run_server.py"

# 启动声纹情感服务
if (-not $NoVprSer) {
    Write-Host "启动声纹情感服务（端口8002）..." -ForegroundColor Cyan
    Start-DevWindow "Set-Location '$RepoRoot\ai-vpr-ser'; & '$Py' run_server.py"
}

# 启动前端
if (-not $NoFrontend) {
    Write-Host "启动前端服务（端口5173）..." -ForegroundColor Cyan
    # 使用 npm 的完整路径，并设置 PATH 包含 nodejs
    $NpmPath = "C:\Program Files\nodejs\npm.cmd"
    $NodePath = "C:\Program Files\nodejs"
    if (Test-Path $NpmPath) {
        # 在新窗口中先添加 Node.js 到 PATH，然后运行 npm
        $frontendCmd = "`$env:PATH += ';$NodePath'; Set-Location '$RepoRoot\frontend'; & '$NpmPath' install; & '$NpmPath' run dev"
        Start-DevWindow $frontendCmd
    } else {
        Write-Host "警告：未找到 npm，请确保 Node.js 已正确安装" -ForegroundColor Yellow
        Write-Host "可以尝试手动运行: cd frontend; npm install; npm run dev" -ForegroundColor Yellow
    }
}

Write-Host "所有服务启动完成！" -ForegroundColor Green
Write-Host "前端访问地址：http://localhost:5173" -ForegroundColor Green