@echo off
setlocal

echo ===================================================
echo Nexus Framework - Secure API Key Setup
echo ===================================================
echo.

:: Check if secure dependencies are installed
python -c "import cryptography, keyring" 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo Installing secure dependencies...
    pip install cryptography keyring
    if %ERRORLEVEL% NEQ 0 (
        echo.
        echo ERROR: Failed to install secure dependencies.
        echo Falling back to basic key management.
        echo.
    ) else (
        echo Secure dependencies installed successfully!
    )
)

echo.
echo This wizard will help you set up API keys securely for LLM providers.
echo.
echo SECURITY NOTE: This project is stored in a public repository.
echo Never commit any actual API keys to GitHub.
echo.
echo Available providers:
echo  - Google (Gemini models)
echo  - Anthropic (Claude models)
echo  - OpenAI (GPT models)
echo  - OpenRouter (various models)
echo.
echo Press any key to continue...
pause > nul

:: Create the API key template if it doesn't exist
if not exist api_keys.template.json (
    echo Creating API key template...
    echo {> api_keys.template.json
    echo   "google": "YOUR_GOOGLE_API_KEY",>> api_keys.template.json
    echo   "anthropic": "YOUR_ANTHROPIC_API_KEY",>> api_keys.template.json
    echo   "openai": "YOUR_OPENAI_API_KEY",>> api_keys.template.json
    echo   "openrouter": "YOUR_OPENROUTER_API_KEY">> api_keys.template.json
    echo }>> api_keys.template.json
)

:: Run the interactive setup
python -c "from nexus_framework.llm_key_manager import LLMKeyManager; LLMKeyManager().interactive_setup()"

echo.
echo ===================================================
echo Setup Complete
echo ===================================================
echo.
echo Security Recommendations:
echo  1. Use environment variables for production
echo  2. Never commit api_keys.json to version control
echo  3. Regularly rotate your API keys
echo.
echo You can view configured providers by running:
echo python -m nexus_framework.llm_key_manager
echo.
echo To start the Agent Team Builder with these keys:
echo run_simple_team_builder.bat
echo.
echo Press any key to exit...
pause > nul
