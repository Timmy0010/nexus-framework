@echo off
rem Generate comprehensive documentation for LLM reference

echo Generating Nexus Framework documentation...
python generate_documentation.py
echo.
echo Documentation generation complete.
echo The output file is: nexus_framework_documentation.md
echo.
pause
