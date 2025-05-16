@echo off
echo Nexus Framework MCP Integration Installer
echo =========================================
echo.
echo This script will install the Nexus Framework and set up MCP integration.
echo.

:: Check if Python is installed
where python >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo Error: Python is not installed or not in the PATH.
    echo Please install Python 3.9 or higher and try again.
    exit /b 1
)

:: Check Python version
for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
echo Detected Python version: %PYTHON_VERSION%
echo.

:: Create a virtual environment if requested
set /p CREATE_VENV=Do you want to create a virtual environment? (y/n): 
if /i "%CREATE_VENV%"=="y" (
    echo Creating virtual environment...
    cd %~dp0
    python -m venv .venv
    if %ERRORLEVEL% neq 0 (
        echo Error: Failed to create virtual environment.
        exit /b 1
    )
    echo Virtual environment created.
    echo Activating virtual environment...
    call .venv\Scripts\activate
    if %ERRORLEVEL% neq 0 (
        echo Error: Failed to activate virtual environment.
        exit /b 1
    )
    echo Virtual environment activated.
)

:: Install the Nexus Framework
echo.
echo Installing Nexus Framework...
cd %~dp0
python -m pip install -e .
if %ERRORLEVEL% neq 0 (
    echo Error: Failed to install Nexus Framework.
    exit /b 1
)
echo Nexus Framework installed successfully.

:: Install additional dependencies
echo.
echo Installing additional dependencies...
python -m pip install pydantic>=2.0.0 python-dateutil>=2.8.2 structlog>=23.1.0 typing-extensions>=4.5.0
if %ERRORLEVEL% neq 0 (
    echo Warning: Some dependencies may not have been installed correctly.
    echo You can manually install them with: pip install pydantic python-dateutil structlog typing-extensions
) else (
    echo Additional dependencies installed successfully.
)

:: Write a small config file
echo.
echo Creating Nexus MCP configuration...
echo {> nexus_mcp_config.json
echo   "mcp_servers": {>> nexus_mcp_config.json
echo     "claude_fetch": {>> nexus_mcp_config.json
echo       "command": "node",>> nexus_mcp_config.json
echo       "args": [>> nexus_mcp_config.json
echo         "%LOCALAPPDATA%\\AnthropicClaude\\app-0.9.3\\fetch-mcp\\dist\\index.js">> nexus_mcp_config.json
echo       ]>> nexus_mcp_config.json
echo     },>> nexus_mcp_config.json
echo     "claude_sqlite": {>> nexus_mcp_config.json
echo       "command": "uvx",>> nexus_mcp_config.json
echo       "args": [>> nexus_mcp_config.json
echo         "mcp-server-sqlite",>> nexus_mcp_config.json
echo         "--db-path",>> nexus_mcp_config.json
echo         "%USERPROFILE%\\TestSQLbase.db">> nexus_mcp_config.json
echo       ]>> nexus_mcp_config.json
echo     }>> nexus_mcp_config.json
echo   }>> nexus_mcp_config.json
echo }>> nexus_mcp_config.json
echo Nexus MCP configuration created.

:: Create a test script
echo.
echo Creating test script...
echo @echo off> run_nexus_mcp_test.bat
echo.>> run_nexus_mcp_test.bat
if /i "%CREATE_VENV%"=="y" (
    echo call %~dp0.venv\Scripts\activate>> run_nexus_mcp_test.bat
)
echo python %~dp0nexus_mcp_test.py>> run_nexus_mcp_test.bat
echo pause>> run_nexus_mcp_test.bat
echo Test script created.

:: Create a launcher for the application
echo.
echo Creating application launcher...
echo @echo off> run_nexus_mcp_app.bat
echo.>> run_nexus_mcp_app.bat
if /i "%CREATE_VENV%"=="y" (
    echo call %~dp0.venv\Scripts\activate>> run_nexus_mcp_app.bat
)
echo python %~dp0nexus_mcp_app.py>> run_nexus_mcp_app.bat
echo pause>> run_nexus_mcp_app.bat
echo Application launcher created.

:: Provide instructions for use
echo.
echo =========================================
echo Installation Complete!
echo =========================================
echo.
echo To run the Nexus MCP integration test:
echo   Double-click run_nexus_mcp_test.bat
echo.
echo To run the Nexus MCP application:
echo   Double-click run_nexus_mcp_app.bat
echo.
echo Make sure Claude Desktop is running for MCP features to work correctly.
echo.
if /i "%CREATE_VENV%"=="y" (
    echo Note: Virtual environment will be activated automatically by these scripts.
    echo If you want to run manually, first activate the environment:
    echo   call %~dp0.venv\Scripts\activate
    echo.
)
echo For documentation, refer to the LLM_INSTRUCTIONS.md file.
echo.
echo =========================================
echo.
pause
