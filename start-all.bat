@echo off
echo ========================================
echo Starting All Services
echo ========================================
echo.

echo Starting Backend Service (Port 8000)...
:: Run Backend from its own directory using its .venv
start "Backend Service" cmd /k "cd /d "%~dp0Backend" && IF EXIST .venv\Scripts\python.exe (.venv\Scripts\python.exe -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload) ELSE (echo Error: Backend .venv not found! & pause)"
timeout /t 3 /nobreak >nul

echo Starting Interceptor Service (Port 8001)...
:: Run Interceptor from its own directory using its .venv (safer than running from Backend dir)
start "Interceptor Service" cmd /k "cd /d "%~dp0Interceptor" && IF EXIST .venv\Scripts\python.exe (.venv\Scripts\python.exe -m uvicorn main:app --host 0.0.0.0 --port 8001 --reload) ELSE (echo Error: Interceptor .venv not found! & pause)"
timeout /t 3 /nobreak >nul

echo Starting Frontend (Port 5173)...
start "Frontend" cmd /k "cd /d "%~dp0Frontend" && npm run dev"

echo.
echo ========================================
echo All services started!
echo ========================================
echo Backend:      http://localhost:8000
echo Interceptor:  http://localhost:8001
echo Frontend:     http://localhost:5173
echo ========================================
echo.
echo Press any key to exit...
pause >nul
