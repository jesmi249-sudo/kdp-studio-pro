@echo off
echo Building KDP Studio Pro...

if not exist ".venv\Scripts\python.exe" (
    echo ERROR: Virtual environment not found. Please run 'python -m venv .venv' and install requirements.
    pause
    exit /b 1
)

.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\pyinstaller KDP_Studio_Pro.spec --clean
echo Build complete! Check the 'dist' folder.
pause
