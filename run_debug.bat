@echo off
echo Starting Anime Tracker in Debug Mode...
set PYTHONPATH=%CD%\src
python -u src\main.py 2>&1 | findstr /V "^$"
pause