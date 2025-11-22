#!/bin/bash

# Azure DevOps Self-Hosted Agent Setup for GCP VM (Linux)
# Complete automated setup script
# Copy and paste this entire script into your GCP VM terminal

set -e

echo "🚀 Setting up Azure DevOps Self-Hosted Agent on GCP VM..."
echo "=================================================="
echo "VM IP: $(curl -s ifconfig.me)"
echo "Hostname: $(hostname)"
echo "User: $(whoami)"
echo "Date: $(date)"
echo "=================================================="

# Update system
echo "📦 Updating system packages..."
sudo apt update && sudo apt upgrade -y

# Install required dependencies
echo "🔧 Installing dependencies..."
sudo apt install -y curl wget jq unzip

# Install .NET Core (required for Azure DevOps agent)
echo "📦 Installing .NET Core..."
# Detect OS version
if [ -f /etc/os-release ]; then
    . /etc/os-release
    OS_VERSION="${VERSION_ID}"
    OS_NAME="${ID}"
else
    OS_NAME="ubuntu"
    OS_VERSION="20.04"
fi

echo "Detected OS: $OS_NAME $OS_VERSION"

# Install .NET based on OS
if [[ "$OS_NAME" == "ubuntu" ]]; then
    wget https://packages.microsoft.com/config/ubuntu/${OS_VERSION}/packages-microsoft-prod.deb -O packages-microsoft-prod.deb
    sudo dpkg -i packages-microsoft-prod.deb
    sudo apt-get update
    sudo apt-get install -y apt-transport-https
    sudo apt-get update
    sudo apt-get install -y dotnet-runtime-6.0 || sudo apt-get install -y dotnet-runtime-8.0
elif [[ "$OS_NAME" == "debian" ]]; then
    wget https://packages.microsoft.com/config/debian/${OS_VERSION}/packages-microsoft-prod.deb -O packages-microsoft-prod.deb
    sudo dpkg -i packages-microsoft-prod.deb
    sudo apt-get update
    sudo apt-get install -y apt-transport-https
    sudo apt-get update
    sudo apt-get install -y dotnet-runtime-6.0 || sudo apt-get install -y dotnet-runtime-8.0
fi

# Clean up
rm -f packages-microsoft-prod.deb

# Create agent directory
echo "📁 Creating agent directory..."
sudo mkdir -p /opt/azuredevops-agent
sudo chown $USER:$USER /opt/azuredevops-agent
cd /opt/azuredevops-agent

# Download Azure DevOps agent
echo "⬇️ Downloading Azure DevOps agent..."
AGENT_VERSION="3.232.0"
wget https://vstsagentpackage.azureedge.net/agent/${AGENT_VERSION}/vsts-agent-linux-x64-${AGENT_VERSION}.tar.gz

# Extract agent
echo "📂 Extracting agent..."
tar zxvf vsts-agent-linux-x64-${AGENT_VERSION}.tar.gz

# Clean up
rm vsts-agent-linux-x64-${AGENT_VERSION}.tar.gz

# Install dependencies
echo "🔧 Installing agent dependencies..."
sudo ./bin/installdependencies.sh

echo ""
echo "✅ Agent download and setup completed!"
echo ""
echo "🔑 Next steps - Configuration:"
echo "================================"
echo "1. Create Personal Access Token:"
echo "   - Go to: https://dev.azure.com/mdsajid020/_usersSettings/tokens"
echo "   - Name: GCPSelfHostedAgent"
echo "   - Scopes: Agent Pools (Read & manage)"
echo ""
echo "2. Configure the agent:"
echo "   ./config.sh"
echo ""
echo "3. When prompted, use these values:"
echo "   Server URL: https://dev.azure.com/mdsajid020"
echo "   Authentication type: PAT"
echo "   Personal Access Token: [Your PAT token]"
echo "   Agent pool: Default"
echo "   Agent name: GCP-SelfHostedAgent"
echo "   Work folder: _work"
echo "   Run as service: Y"
echo ""
echo "4. Start the agent:"
echo "   sudo ./svc.sh install"
echo "   sudo ./svc.sh start"
echo ""
echo "5. Verify agent status:"
echo "   sudo ./svc.sh status"
echo ""
echo "📋 Manual configuration commands:"
echo "cd /opt/azuredevops-agent"
echo "./config.sh"
echo "sudo ./svc.sh install"
echo "sudo ./svc.sh start"
echo ""
echo "🎉 After setup, your pipeline will run on this GCP VM!"
echo ""
echo "📊 System Information:"
echo "======================"
echo "OS: $(lsb_release -d 2>/dev/null | cut -f2 || echo 'Unknown')"
echo "Architecture: $(uname -m)"
echo "Kernel: $(uname -r)"
echo "Memory: $(free -h | grep '^Mem:' | awk '{print $2}')"
echo "Disk Space: $(df -h / | tail -1 | awk '{print $4}' | sed 's/G/ GB/')"
echo "CPU Cores: $(nproc)"
echo ""
echo "✅ Setup completed! Ready for Azure DevOps agent configuration."