@echo off
echo ========================================
echo Starting All Services
echo ========================================
echo.

echo Starting Backend Service (Port 8000)...
start "Backend Service" cmd /k "cd /d "%~dp0Backend" && venv\Scripts\python.exe -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload"
timeout /t 3 /nobreak >nul

echo Starting Interceptor Service (Port 8001)...
start "Interceptor Service" cmd /k "cd /d "%~dp0Backend" && venv\Scripts\python.exe -m uvicorn ..\Interceptor\main:app --host 127.0.0.1 --port 8001 --reload"
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
