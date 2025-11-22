#!/bin/bash

# GCP VM Deployment Script for Shift Handover App
# Run this script on your GCP VM to deploy the application

set -e

echo "🚀 Starting deployment of Shift Handover App on GCP VM..."

# Update system packages
echo "📦 Updating system packages..."
sudo apt-get update -y
sudo apt-get upgrade -y

# Install Docker if not installed
if ! command -v docker &> /dev/null; then
    echo "🐳 Installing Docker..."
    sudo apt-get install -y apt-transport-https ca-certificates curl gnupg lsb-release
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
    echo "deb [arch=amd64 signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
    sudo apt-get update -y
    sudo apt-get install -y docker-ce docker-ce-cli containerd.io
    sudo usermod -aG docker $USER
fi

# Install Docker Compose if not installed
if ! command -v docker-compose &> /dev/null; then
    echo "🐳 Installing Docker Compose..."
    sudo curl -L "https://github.com/docker/compose/releases/download/v2.20.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    sudo chmod +x /usr/local/bin/docker-compose
fi

# Install Git if not installed
if ! command -v git &> /dev/null; then
    echo "📁 Installing Git..."
    sudo apt-get install -y git
fi

# Create application directory
APP_DIR="/opt/shift-handover-app"
echo "📁 Creating application directory at $APP_DIR..."
sudo mkdir -p $APP_DIR
sudo chown $USER:$USER $APP_DIR

# Clone or update the application
if [ -d "$APP_DIR/.git" ]; then
    echo "🔄 Updating existing application..."
    cd $APP_DIR
    git pull
else
    echo "📥 Cloning application..."
    # You'll need to replace this with your actual repository URL
    echo "Please clone your repository manually to $APP_DIR"
    echo "Example: git clone <your-repo-url> $APP_DIR"
    exit 1
fi

cd $APP_DIR

# Copy environment file
if [ ! -f ".env" ]; then
    echo "⚙️ Creating environment file..."
    cp .env.production .env
    echo "🚨 IMPORTANT: Please edit .env with your actual configuration values!"
    echo "   nano .env"
    read -p "Press Enter after you've configured the .env file..."
fi

# Build and start the application
echo "🏗️ Building and starting the application..."
docker-compose -f docker-compose.prod.yml down
docker-compose -f docker-compose.prod.yml build --no-cache
docker-compose -f docker-compose.prod.yml up -d

# Configure firewall
echo "🔥 Configuring firewall..."
sudo ufw allow 80
sudo ufw allow 443
sudo ufw allow ssh

# Setup SSL (optional - requires domain)
echo "🔒 For SSL setup, you can use certbot with nginx reverse proxy"
echo "   This is optional and requires a domain name"

# Show status
echo "📊 Application status:"
docker-compose -f docker-compose.prod.yml ps

# Get VM external IP
EXTERNAL_IP=$(curl -s http://metadata.google.internal/computeMetadata/v1/instance/network-interfaces/0/access-configs/0/external-ip -H "Metadata-Flavor: Google")

echo ""
echo "✅ Deployment completed!"
echo "🌐 Application should be accessible at: http://$EXTERNAL_IP"
echo "📝 Logs: docker-compose -f docker-compose.prod.yml logs -f"
echo "🔄 Restart: docker-compose -f docker-compose.prod.yml restart"
echo "🛑 Stop: docker-compose -f docker-compose.prod.yml down"
echo ""
echo "🚨 Remember to:"
echo "   1. Configure your database connection in .env"
echo "   2. Set up proper email credentials"
echo "   3. Configure ServiceNow if needed"
echo "   4. Set up SSL certificate for production use"