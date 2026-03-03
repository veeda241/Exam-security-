@echo off
TITLE ExamGuard Pro - Secure Launch
COLOR 0A

echo ====================================================
echo      ExamGuard Pro - Security System Launch
echo ====================================================
echo.

:: 1. Check Python Environment
echo [1/4] Checking Python Environment...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python not found! Please install Python 3.10+
    pause
    exit /b 1
)

:: 2. Activate Virtual Environment (if exists)
if exist ".venv\Scripts\activate.bat" (
    echo [2/4] Activating Virtual Environment...
    call .venv\Scripts\activate.bat
) else (
    echo [WARN] Virtual environment not found. Using global python.
)

:: 3. Launch Server in Background
echo [3/4] Starting AI Server (Face + Transformer)...
start "ExamGuard Server" /min cmd /k "python server/main.py"
echo    - Server running at http://localhost:8000
echo    - API Docs at http://localhost:8000/docs

:: 4. Launch Dashboard
echo [4/4] Launching Proctor Dashboard...
timeout /t 5 /nobreak >nul
start http://localhost:8000/dashboard

echo.
echo ====================================================
echo      SYSTEM ONLINE - MONITORING ACTIVE
echo ====================================================
echo.
echo Press any key to stop the server...
pause >nul

taskkill /F /IM python.exe /T >nul 2>&1
echo System Shutdown Complete.
