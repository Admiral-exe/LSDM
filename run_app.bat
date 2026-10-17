@echo off
title Laboratory Supply & Sample Management System
echo ======================================================================
echo Starting Laboratory Supply & Sample Management Desktop System...
echo 100%% Offline Mode - SQLite Engine with Two-Way Atomic Excel Sync
echo ======================================================================
cd /d "%~dp0"
if exist .venv\Scripts\python.exe (
    .\.venv\Scripts\python.exe main.py %*
) else (
    python main.py %*
)
pause
