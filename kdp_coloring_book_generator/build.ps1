# build.ps1
# This script builds the standalone Windows executable using PyInstaller.

$ErrorActionPreference = "Stop"

Write-Host "Verifying Python installation..." -ForegroundColor Cyan
if (-not (Get-Command "python" -ErrorAction SilentlyContinue)) {
    Write-Host "ERROR: Python is not installed or not in PATH." -ForegroundColor Red
    Write-Host "Please install Python from https://www.python.org/downloads/ and check 'Add Python to PATH'." -ForegroundColor Yellow
    exit 1
}

Write-Host "Installing dependencies..." -ForegroundColor Cyan
python -m pip install -r requirements.txt

Write-Host "Installing PyInstaller..." -ForegroundColor Cyan
python -m pip install pyinstaller

Write-Host "Cleaning previous builds..." -ForegroundColor Cyan
if (Test-Path "build") { Remove-Item -Recurse -Force "build" }
if (Test-Path "dist") { Remove-Item -Recurse -Force "dist" }

Write-Host "Building KDP Coloring Book Generator..." -ForegroundColor Cyan
# Run pyinstaller with the spec file
pyinstaller build.spec --clean

Write-Host "Build complete! Executable is located in the 'dist' folder." -ForegroundColor Green
