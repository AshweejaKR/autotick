@echo off
cd /d "%~dp0"
python -m autotick.swing_watchlist_tool
if errorlevel 1 pause
