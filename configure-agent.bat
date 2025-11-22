@echo off
echo 🚀 Azure DevOps Self-Hosted Agent Configuration
echo.

REM Check if agent.zip exists
if not exist "C:\agent\agent.zip" (
    echo ❌ agent.zip not found in C:\agent\
    echo Please download the agent first:
    echo https://vstsagentpackage.azureedge.net/agent/3.232.0/vsts-agent-win-x64-3.232.0.zip
    echo Save it as: C:\agent\agent.zip
    pause
    exit /b 1
)

echo ✅ Found agent.zip
echo.

REM Extract agent
echo 📂 Extracting agent...
cd /d "C:\agent"
powershell -Command "Expand-Archive -Path 'agent.zip' -DestinationPath '.' -Force"

REM Clean up
echo 🧹 Cleaning up...
del agent.zip

echo.
echo ⚙️ Starting agent configuration...
echo.
echo You will be prompted for:
echo   Server URL: https://dev.azure.com/mdsajid020
echo   Authentication: PAT
echo   Personal Access Token: [Your PAT token]
echo   Agent pool: Default
echo   Agent name: SelfHostedAgent
echo   Work folder: _work
echo   Run as service: Y
echo.

REM Configure agent
config.cmd

echo.
echo ✅ Configuration completed!
echo 🚀 Starting agent...

REM Start agent
run.cmd