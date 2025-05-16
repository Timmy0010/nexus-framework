@echo off
echo Creating Nexus MCP Desktop Shortcut
echo ==================================
echo.

:: Get the full path to the start script
set START_SCRIPT=%~dp0start_nexus_mcp.bat
echo Start script path: %START_SCRIPT%

:: Create a temporary VBScript to create the shortcut
echo Set oWS = WScript.CreateObject("WScript.Shell") > CreateShortcut.vbs
echo sLinkFile = oWS.SpecialFolders("Desktop") ^& "\Nexus MCP Application.lnk" >> CreateShortcut.vbs
echo Set oLink = oWS.CreateShortcut(sLinkFile) >> CreateShortcut.vbs
echo oLink.TargetPath = "%START_SCRIPT%" >> CreateShortcut.vbs
echo oLink.IconLocation = "%SystemRoot%\System32\imageres.dll,73" >> CreateShortcut.vbs
echo oLink.Description = "Start Nexus Framework with MCP Integration" >> CreateShortcut.vbs
echo oLink.WorkingDirectory = "%~dp0" >> CreateShortcut.vbs
echo oLink.Save >> CreateShortcut.vbs

:: Run the VBScript to create the shortcut
cscript /nologo CreateShortcut.vbs

:: Delete the temporary VBScript
del CreateShortcut.vbs

echo.
echo Desktop shortcut created successfully!
echo You can now launch the Nexus MCP Application directly from your desktop.
echo.
pause
