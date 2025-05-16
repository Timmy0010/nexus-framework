@echo off
echo Running Reliable Team Example with Message Broker
echo.
echo This example demonstrates the reliable messaging infrastructure
echo with guaranteed message delivery and acknowledgments.
echo.
echo Note: This example requires RabbitMQ to be installed and running.
echo If RabbitMQ is not available, it will fall back to legacy mode.
echo.

python reliable_team_example.py

echo.
echo Example completed. See reliable_team_conversation.txt for the transcript.
pause
