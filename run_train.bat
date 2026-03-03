
@echo off
echo Starting batch script... > train_log.txt
echo Using python from .venv >> train_log.txt
cmd /c ".venv\Scripts\python.exe" transformer/train_examguard.py >> train_log.txt 2>&1
echo Script finished with error code %errorlevel% >> train_log.txt
