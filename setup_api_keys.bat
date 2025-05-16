@echo off
echo Secure API Key Setup for Nexus Framework
python -c "from nexus_framework.llm_key_manager import LLMKeyManager; LLMKeyManager().interactive_setup()"
pause
