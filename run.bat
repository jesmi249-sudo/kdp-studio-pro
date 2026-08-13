@echo off
echo Starting KDP Studio Pro...

if not exist ".venv\Scripts\python.exe" (
    echo ERROR: Virtual environment not found. Please run 'python -m venv .venv' and install requirements.
    pause
    exit /b 1
)

.venv\Scripts\python.exe main.py
pause
