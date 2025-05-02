@echo off
echo Setting up Shift Management Dashboard...
echo.

:: Check if Python is installed
python --version > nul 2>&1
if errorlevel 1 (
    echo Python is not installed! Please install Python first.
    echo Visit: https://www.python.org/downloads/
    pause
    exit
)

:: Create virtual environment if it doesn't exist
if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
)

:: Activate virtual environment and install requirements
echo Installing required packages...
call venv\Scripts\activate.bat
pip install -r requirements.txt

echo.
echo Setup complete! You can now use start_dashboard.bat to run the dashboard.
echo.
pause 