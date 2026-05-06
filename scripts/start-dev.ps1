<#
.SYNOPSIS
  一键在本机打开多个终端窗口，启动后端、ASR、声纹情感、前端（可选）。

.DESCRIPTION
  默认端口：后端 8000、ASR 8090、ai-vpr-ser 8002、前端 5173。
  使用仓库根目录 .venv 中的 Python；前端需本机已安装 Node 并可在 PATH 中找到 npm，
  否则会自动尝试 "C:\Program Files\nodejs"。

.PARAMETER NoFrontend
  不启动前端（仅 Python 三服务）。

.PARAMETER NoVprSer
  不启动 ai-vpr-ser。
#>
[CmdletBinding()]
param(
    [switch] $NoFrontend,
    [switch] $NoVprSer
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $RepoRoot

$Py = Join-Path $RepoRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $Py)) {
    Write-Host "未找到 $Py ，请先在仓库根目录执行: python -m venv .venv && .\.venv\Scripts\pip install -r requirements.txt" -ForegroundColor Red
    exit 1
}

function Start-DevWindow {
    param([string] $Command)
    Start-Process powershell.exe -ArgumentList @("-NoExit", "-NoLogo", "-Command", $Command) -WorkingDirectory $RepoRoot
}

Write-Host "仓库根: $RepoRoot" -ForegroundColor Cyan
Write-Host "将打开新窗口启动各服务（关闭对应窗口即停止该服务）…" -ForegroundColor Cyan

$backendCmd = "Set-Location '$RepoRoot\backend'; & '$Py' run_server.py"
Start-DevWindow $backendCmd

$asrCmd = "Set-Location '$RepoRoot\ai-asr'; & '$Py' run_server.py"
Start-DevWindow $asrCmd

if (-not $NoVprSer) {
    $vprCmd = "Set-Location '$RepoRoot\ai-vpr-ser'; & '$Py' run_server.py"
    Start-DevWindow $vprCmd
}

if (-not $NoFrontend) {
    $npmExe = "npm"
    foreach ($dir in @(
            "C:\Program Files\nodejs",
            "$env:ProgramFiles\nodejs",
            "$env:LOCALAPPDATA\Programs\node"
        )) {
        $c = Join-Path $dir "npm.cmd"
        if (Test-Path $c) {
            $npmExe = $c
            break
        }
    }
    $feCmd = "Set-Location '$RepoRoot\frontend'; if (-not (Test-Path 'node_modules')) { & '$npmExe' install }; & '$npmExe' run dev"
    Start-DevWindow $feCmd
}

Write-Host "已启动。前端地址一般为 http://localhost:5173" -ForegroundColor Green
Write-Host "停止全部可用:  .\scripts\stop-dev.ps1   或关闭各窗口。" -ForegroundColor DarkGray
