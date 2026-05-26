@echo off
REM FYS Packet Creator. One-click start script for Windows.

cd /d "%~dp0"

echo.
echo ============================================================
echo   FYS Packet Creator
echo ============================================================
echo.

REM Check that Python is available.
where python >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not on PATH.
    echo.
    echo Install Python 3.9 or newer from https://python.org/downloads
    echo During install, check "Add Python to PATH".
    echo.
    pause
    exit /b 1
)

REM Install dependencies. Quiet on subsequent runs.
echo Checking dependencies...
python -m pip install --quiet --disable-pip-version-check -r requirements.txt
if errorlevel 1 (
    echo.
    echo Failed to install dependencies. Try running:
    echo   pip install -r requirements.txt
    echo manually and check the error.
    pause
    exit /b 1
)

echo Dependencies OK.
echo.
echo Starting the server at http://localhost:5050 ...
echo (Leave this window open while you use the tool. Press Ctrl+C to stop.)
echo.

REM Open the browser after a short delay so the server is up first.
start "" /b cmd /c "timeout /t 3 /nobreak >nul && start http://localhost:5050"

python app.py
