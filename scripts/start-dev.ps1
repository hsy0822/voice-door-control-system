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
    
    # 智能检测 Node.js 路径
    $NpmPath = $null
    
    # 方法1: 检查是否在 PATH 中（推荐）
    try {
        $npmInPath = Get-Command npm -ErrorAction SilentlyContinue
        if ($npmInPath) {
            # 如果是 .ps1 文件，尝试找到对应的 .cmd 文件
            $npmSource = $npmInPath.Source
            if ($npmSource -like "*.ps1") {
                $cmdPath = $npmSource -replace '\.ps1$', '.cmd'
                if (Test-Path $cmdPath) {
                    $NpmPath = $cmdPath
                } else {
                    $NpmPath = $npmSource
                }
            } else {
                $NpmPath = $npmSource
            }
        }
    } catch {
        # 忽略错误
    }
    
    # 方法2: 检查常见安装位置
    if (-not $NpmPath) {
        $commonPaths = @(
            "C:\Program Files\nodejs\npm.cmd",
            "C:\Program Files (x86)\nodejs\npm.cmd",
            "$env:APPDATA\npm\npm.cmd"
        )
        
        foreach ($path in $commonPaths) {
            if (Test-Path $path) {
                $NpmPath = $path
                break
            }
        }
    }
    
    # 方法3: 通过 where.exe 查找
    if (-not $NpmPath) {
        try {
            $whereResult = & where.exe npm 2>$null
            if ($whereResult) {
                $NpmPath = $whereResult[0]
            }
        } catch {
            # 忽略错误
        }
    }
    
    if ($NpmPath) {
        $NodeDir = Split-Path $NpmPath -Parent
        # 在新窗口中先添加 Node.js 到 PATH，然后运行 npm
        $frontendCmd = "`$env:PATH += ';$NodeDir'; Set-Location '$RepoRoot\frontend'; & '$NpmPath' install; & '$NpmPath' run dev"
        Start-DevWindow $frontendCmd
    } else {
        Write-Host "❌ 错误：未找到 npm！" -ForegroundColor Red
        Write-Host "请确保 Node.js 已正确安装并添加到系统 PATH" -ForegroundColor Yellow
        Write-Host ""
        Write-Host "常见解决方法：" -ForegroundColor Cyan
        Write-Host "1. 重新安装 Node.js 并勾选 'Add to PATH'" -ForegroundColor White
        Write-Host "2. 手动设置环境变量 NODE_PATH" -ForegroundColor White
        exit 1
    }
}

Write-Host "所有服务启动完成！" -ForegroundColor Green
Write-Host "前端访问地址：http://localhost:5173" -ForegroundColor Green