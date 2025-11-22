Write-Host " Setting up Azure DevOps Self-Hosted Agent..." -ForegroundColor Green

# Download and extract agent
$agentUrl = "https://vstsagentpackage.azureedge.net/agent/3.243.1/vsts-agent-win-x64-3.243.1.zip"
$agentZip = "vsts-agent-win-x64-3.243.1.zip"
$agentDir = "C:\agent"

Write-Host " Creating agent directory..." -ForegroundColor Yellow
New-Item -ItemType Directory -Path $agentDir -Force

Write-Host " Downloading Azure DevOps agent..." -ForegroundColor Yellow
Invoke-WebRequest -Uri $agentUrl -OutFile $agentZip

Write-Host " Extracting agent..." -ForegroundColor Yellow
Expand-Archive -Path $agentZip -DestinationPath $agentDir -Force

Write-Host " Cleaning up..." -ForegroundColor Yellow
Remove-Item $agentZip

Write-Host " Agent download completed!" -ForegroundColor Green
