@echo off
title Darkroom DataForge - Starter
echo ================================================================
echo   DARKROOM DATAFORGE - Launching Web Platform
echo   Wits-merSETA Darkroom Document Intelligence Workstation
echo ================================================================

echo Starting Backend Server on http://127.0.0.1:8000 ...
start "DataForge Backend" cmd /k ".venv\Scripts\python run_dev.py"

timeout /t 2 /nobreak >nul

echo Starting Frontend Dev Server on http://localhost:5173 ...
start "DataForge Frontend" cmd /k "cd frontend && npm run dev"

echo Both services launched in separate windows!
echo Backend:  http://127.0.0.1:8000/docs
echo Frontend: http://localhost:5173
