@echo off
REM Setup script for TIDAL Playlist Monitor on Windows

echo ========================================
echo TIDAL Playlist Monitor - Windows Setup
echo ========================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.12 or 3.13 from python.org
    pause
    exit /b 1
)

echo [1/5] Creating virtual environment...
python -m venv venv
if %errorlevel% neq 0 (
    echo ERROR: Failed to create virtual environment
    pause
    exit /b 1
)

echo [2/5] Activating virtual environment...
call venv\Scripts\activate.bat

echo [3/5] Installing dependencies...
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo ERROR: Failed to install dependencies
    pause
    exit /b 1
)

echo [4/5] Checking tidal-dl-ng installation...
tidal-dl-ng --version >nul 2>&1
if %errorlevel% neq 0 (
    echo tidal-dl-ng not found, installing...
    pip install tidal-dl-ng
)

echo [5/5] Initializing configuration...
python -m tidal_playlist_monitor.cli init-config

echo.
echo ========================================
echo Setup Complete!
echo ========================================
echo.
echo Next steps:
echo 1. Authenticate with TIDAL:
echo    tidal-dl-ng login
echo.
echo 2. Add a playlist to monitor:
echo    python -m tidal_playlist_monitor.cli add-playlist "PLAYLIST_URL"
echo.
echo 3. Start the service:
echo    python -m tidal_playlist_monitor.cli start
echo.
echo Configuration file: %APPDATA%\tidal-playlist-monitor\config.yaml
echo.
echo For Windows auto-start setup, see WINDOWS_GUIDE.md
echo.
pause
