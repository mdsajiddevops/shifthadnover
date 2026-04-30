#!/bin/bash

# GCP VM Setup Script for Azure DevOps Deployment
# Run this once on your GCP VM to prepare it for Azure DevOps deployments

set -e

echo "🔧 Setting up GCP VM for Azure DevOps deployment..."

# Update system
sudo apt-get update -y
sudo apt-get upgrade -y

# Install Docker
if ! command -v docker &> /dev/null; then
    echo "🐳 Installing Docker..."
    curl -fsSL https://get.docker.com -o get-docker.sh
    sudo sh get-docker.sh
    sudo usermod -aG docker $USER
    rm get-docker.sh
fi

# Install Docker Compose (optional, for local testing)
if ! command -v docker-compose &> /dev/null; then
    echo "🐳 Installing Docker Compose..."
    sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    sudo chmod +x /usr/local/bin/docker-compose
fi

# Create application directory
APP_DIR="/opt/shift-handover-app"
sudo mkdir -p $APP_DIR
sudo chown $USER:$USER $APP_DIR

# Create environment file template
if [ ! -f "$APP_DIR/.env" ]; then
    echo "📝 Creating environment file..."
    cat > $APP_DIR/.env << 'EOF'
# Production Environment Variables
SECRET_KEY=your-super-secret-production-key-here
FLASK_ENV=production

# Database Configuration
DATABASE_URI=sqlite:///shift_handover.db

# Email Configuration
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password
TEAM_EMAIL=your-email@gmail.com

# ServiceNow Configuration (Optional)
SERVICENOW_INSTANCE=your-instance.service-now.com
SERVICENOW_USERNAME=your-servicenow-username
SERVICENOW_PASSWORD=your-servicenow-password
SERVICENOW_ENABLED=false
EOF
    
    echo "🚨 IMPORTANT: Edit $APP_DIR/.env with your actual configuration!"
    echo "   sudo nano $APP_DIR/.env"
fi

# Configure firewall
echo "🔥 Configuring firewall..."
sudo ufw allow 80
sudo ufw allow 443
sudo ufw allow 22

# Enable Docker service
sudo systemctl enable docker
sudo systemctl start docker

echo ""
echo "✅ GCP VM setup completed!"
echo ""
echo "📋 Next steps:"
echo "1. Edit environment file: sudo nano $APP_DIR/.env"
echo "2. Set up SSH key authentication for Azure DevOps"
echo "3. Configure Azure DevOps service connections"
echo "4. Run your first deployment pipeline"
echo ""
echo "🔑 To generate SSH key for Azure DevOps:"
echo "   ssh-keygen -t rsa -b 4096 -C 'azure-devops@shift-handover'"
echo "   cat ~/.ssh/id_rsa.pub"
echo ""