<#
.SYNOPSIS
  Start backend, ASR, VPR/SER, and frontend in separate PowerShell windows.
#>
[CmdletBinding()]
param(
    [switch]$NoFrontend,
    [switch]$NoVprSer
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $RepoRoot

$Py = Join-Path $RepoRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $Py)) {
    Write-Host "ERROR: venv not found: $Py" -ForegroundColor Red
    Write-Host "Run in repo root: python -m venv .venv" -ForegroundColor Red
    exit 1
}

function Start-DevWindow {
    param([string]$Command)
    Start-Process powershell.exe -ArgumentList "-NoExit", "-Command", $Command
}

Write-Host "Repo: $RepoRoot" -ForegroundColor Cyan
Write-Host "Starting services (close each window to stop that service)..." -ForegroundColor Cyan

Write-Host "Backend :8000" -ForegroundColor Cyan
Start-DevWindow "Set-Location '$RepoRoot\backend'; & '$Py' run_server.py"

Write-Host "ASR :8090 (Whisper)" -ForegroundColor Cyan
$WhisperPt = "D:\soft\base.pt"
if (Test-Path $WhisperPt) {
    Start-DevWindow "`$env:ASR_ENGINE='whisper'; `$env:WHISPER_MODEL='D:/soft/base.pt'; Set-Location '$RepoRoot\ai-asr'; & '$Py' run_server.py"
} else {
    Write-Host "WARN: $WhisperPt not found, ASR may try online download" -ForegroundColor Yellow
    Start-DevWindow "`$env:ASR_ENGINE='whisper'; Set-Location '$RepoRoot\ai-asr'; & '$Py' run_server.py"
}

if (-not $NoVprSer) {
    Write-Host "VPR/SER :8002" -ForegroundColor Cyan
    Start-DevWindow "Set-Location '$RepoRoot\ai-vpr-ser'; & '$Py' run_server.py"
}

if (-not $NoFrontend) {
    Write-Host "Frontend :5173" -ForegroundColor Cyan
    $NpmPath = $null
    $npmCmd = Get-Command npm.cmd -ErrorAction SilentlyContinue
    if ($npmCmd) {
        $NpmPath = $npmCmd.Source
    } else {
        $npmPs1 = Get-Command npm -ErrorAction SilentlyContinue
        if ($npmPs1) {
            $cmdPath = $npmPs1.Source -replace '\.ps1$', '.cmd'
            if (Test-Path $cmdPath) {
                $NpmPath = $cmdPath
            }
        }
    }
    if (-not $NpmPath) {
        $candidates = @(
            "C:\Program Files\nodejs\npm.cmd",
            "C:\Program Files (x86)\nodejs\npm.cmd",
            "$env:APPDATA\npm\npm.cmd"
        )
        foreach ($p in $candidates) {
            if (Test-Path $p) {
                $NpmPath = $p
                break
            }
        }
    }
    if ($NpmPath) {
        $NodeDir = Split-Path $NpmPath -Parent
        $frontendCmd = "`$env:PATH += ';$NodeDir'; Set-Location '$RepoRoot\frontend'; & '$NpmPath' install; & '$NpmPath' run dev"
        Start-DevWindow $frontendCmd
    } else {
        Write-Host "ERROR: npm not found. Install Node.js and add to PATH." -ForegroundColor Red
        exit 1
    }
}

Write-Host "All started. Open http://localhost:5173" -ForegroundColor Green
