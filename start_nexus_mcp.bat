@echo off
echo Nexus Framework with MCP Integration
echo ===================================
echo.
echo Starting Claude MCP Integration Application...
echo.

:: Check if Claude Desktop is running
tasklist /FI "IMAGENAME eq Claude.exe" 2>NUL | find /I /N "Claude.exe">NUL
if "%ERRORLEVEL%"=="0" (
    echo Claude Desktop is running.
) else (
    echo Warning: Claude Desktop does not appear to be running.
    echo For full functionality, please start Claude Desktop.
    echo.
    echo Press any key to continue anyway...
    pause >nul
)

:: Directory of this script
set SCRIPT_DIR=%~dp0

:: Check if we have a virtual environment
if exist "%SCRIPT_DIR%.venv\Scripts\activate.bat" (
    echo Activating virtual environment...
    call "%SCRIPT_DIR%.venv\Scripts\activate.bat"
)

:: Run the Nexus MCP application
echo.
echo Starting Nexus MCP application...
echo.
python "%SCRIPT_DIR%nexus_mcp_app.py"

:: Deactivate virtual environment if we activated it
if exist "%SCRIPT_DIR%.venv\Scripts\activate.bat" (
    call deactivate
)

echo.
echo Application execution completed.
echo.
pause
