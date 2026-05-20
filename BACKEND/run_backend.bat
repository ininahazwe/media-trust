@echo off
REM MFWA MTI Dashboard - Backend Setup

echo.
echo ============================================================
echo   MFWA MTI Dashboard - Backend Setup
echo ============================================================
echo.

echo [1/4] Verification Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo ? Python non trouve
    pause
    exit /b 1
)
echo ? Python found

if not exist venv (
    echo [2/4] Creation virtualenv...
    python -m venv venv
    echo ? Virtualenv created
) else (
    echo [2/4] virtualenv exists
)

echo [3/4] Activation...
call venv\Scripts\activate.bat
echo ? Active

echo [4/4] Installation dependencies...
pip install -r requirements.txt

echo.
echo ============================================================
echo   ?? Lancement backend...
echo   ?? http://localhost:8000
echo   Ctrl+C pour arreter
echo ============================================================
echo.

python main.py

pause
