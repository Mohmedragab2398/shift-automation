@echo off
echo Starting Shift Management Dashboard...
echo.

:: Activate virtual environment
call venv\Scripts\activate.bat

:: Start the dashboard
streamlit run app.py

:: Keep the window open if there's an error
pause 