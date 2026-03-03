@echo off
cd server
call .venv\Scripts\activate.bat
python main.py > ..\debug.log 2>&1
