@echo off
echo ========================================
echo Stopping All Services
echo ========================================
echo.

echo Stopping Backend Service (Port 8000)...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":8000.*LISTENING"') do taskkill /F /PID %%a >nul 2>&1
echo Done.

echo Stopping Interceptor Service (Port 8001)...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":8001.*LISTENING"') do taskkill /F /PID %%a >nul 2>&1
echo Done.

echo Stopping Frontend (Port 5173)...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":5173.*LISTENING"') do taskkill /F /PID %%a >nul 2>&1
echo Done.

echo.
echo ========================================
echo All services stopped!
echo ========================================
echo.
echo Press any key to exit...
pause >nul
