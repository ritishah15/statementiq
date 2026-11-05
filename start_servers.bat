@echo off
echo ========================================================
echo Starting StatementIQ - Bank Statement Processing System
echo ========================================================

echo [1/2] Launching FastAPI Backend on http://127.0.0.1:8000 ...
start "StatementIQ Backend" cmd /k "python backend/run.py"

timeout /t 2 /nobreak >nul

echo [2/2] Launching React Vite Frontend on http://localhost:5173 ...
start "StatementIQ Frontend" cmd /k "npm.cmd run dev --prefix frontend"

echo.
echo StatementIQ is running!
echo - Web Dashboard: http://localhost:5173
echo - API Docs (Swagger): http://127.0.0.1:8000/docs
echo ========================================================
