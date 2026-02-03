@echo off
REM ExamGuard Pro - Startup Script for Windows

echo.
echo ============================================
echo  ExamGuard Pro - Backend Server
echo ============================================
echo.

REM Change to server directory
cd /d %~dp0server

REM Check if virtual environment exists
if not exist .venv (
    echo Creating virtual environment...
    python -m venv .venv
)

REM Activate virtual environment
call .venv\Scripts\activate.bat

REM Install dependencies
echo.
echo Checking dependencies...
pip install -r requirements.txt -q

echo.
echo ============================================
echo  Starting Backend API Server
echo ============================================
echo.
echo API is starting...
echo.
echo Access the API:
echo   - http://localhost:8000
echo   - http://127.0.0.1:8000
echo.
echo API Documentation:
echo   - http://localhost:8000/docs
echo.

REM Run the server
python -m uvicorn main:app --host 0.0.0.0 --port 8000

pause
