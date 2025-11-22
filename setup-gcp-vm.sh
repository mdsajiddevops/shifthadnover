#!/bin/bash
# GCP VM Setup Script for Shift Handover Application
# Run this script on your GCP VM to prepare it for Azure DevOps deployment

set -e

echo "🚀 Setting up GCP VM for Shift Handover Application deployment..."

# Update system packages
echo "📦 Updating system packages..."
sudo apt update && sudo apt upgrade -y

# Install Docker if not present
if ! command -v docker &> /dev/null; then
    echo "🐳 Installing Docker..."
    sudo apt install -y docker.io docker-compose
    sudo systemctl start docker
    sudo systemctl enable docker
    
    # Add current user to docker group
    sudo usermod -aG docker $USER
    echo "✅ Docker installed. Please logout and login again for group changes to take effect."
else
    echo "✅ Docker is already installed"
fi

# Install curl and other utilities
echo "🛠️ Installing utilities..."
sudo apt install -y curl wget git htop jq

# Install Azure CLI for ACR access
echo "☁️ Installing Azure CLI for Azure Container Registry access..."
if ! command -v az &> /dev/null; then
    curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash
    echo "✅ Azure CLI installed successfully"
else
    echo "✅ Azure CLI is already installed"
fi

# Create application directories
echo "📁 Creating application directories..."
sudo mkdir -p /opt/shift-handover-data
sudo mkdir -p /opt/shift-handover-uploads
sudo mkdir -p /opt/shift-handover-logs

# Set proper permissions
sudo chown -R $USER:$USER /opt/shift-handover-*
chmod 755 /opt/shift-handover-*

# Configure firewall (if ufw is enabled)
if sudo ufw status | grep -q "Status: active"; then
    echo "🔥 Configuring firewall..."
    sudo ufw allow 22/tcp   # SSH
    sudo ufw allow 80/tcp   # HTTP
    sudo ufw allow 443/tcp  # HTTPS
    echo "✅ Firewall configured"
else
    echo "ℹ️ UFW firewall is not active"
fi

# Create systemd service for Docker container (optional)
echo "⚙️ Creating systemd service template..."
sudo tee /etc/systemd/system/shift-handover.service > /dev/null <<EOF
[Unit]
Description=Shift Handover Application
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
ExecStart=/usr/bin/docker start shift-handover-app
ExecStop=/usr/bin/docker stop shift-handover-app
TimeoutStartSec=0

[Install]
WantedBy=multi-user.target
EOF

# Enable the service (but don't start it yet)
sudo systemctl enable shift-handover.service

# Create a backup script
echo "💾 Creating backup script..."
sudo tee /opt/shift-handover-backup.sh > /dev/null <<'EOF'
#!/bin/bash
# Backup script for Shift Handover Application

BACKUP_DIR="/opt/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Create backup directory
mkdir -p $BACKUP_DIR

# Backup database (if using SQLite)
if [ -f "/opt/shift-handover-data/shift_handover.db" ]; then
    echo "📁 Backing up SQLite database..."
    cp /opt/shift-handover-data/shift_handover.db $BACKUP_DIR/database_$TIMESTAMP.db
fi

# Backup uploads
if [ -d "/opt/shift-handover-uploads" ]; then
    echo "📁 Backing up uploads..."
    tar -czf $BACKUP_DIR/uploads_$TIMESTAMP.tar.gz -C /opt/shift-handover-uploads .
fi

# Keep only last 7 days of backups
find $BACKUP_DIR -name "*.db" -mtime +7 -delete
find $BACKUP_DIR -name "*.tar.gz" -mtime +7 -delete

echo "✅ Backup completed: $TIMESTAMP"
EOF

chmod +x /opt/shift-handover-backup.sh

# Create a maintenance script
echo "🔧 Creating maintenance script..."
sudo tee /opt/shift-handover-maintenance.sh > /dev/null <<'EOF'
#!/bin/bash
# Maintenance script for Shift Handover Application

echo "🧹 Running maintenance tasks..."

# Clean up Docker
echo "🐳 Cleaning up Docker..."
docker system prune -f
docker image prune -f

# Clean up logs (keep last 30 days)
echo "📝 Cleaning up old logs..."
find /opt/shift-handover-logs -name "*.log" -mtime +30 -delete

# Check disk space
echo "💾 Disk space usage:"
df -h /opt

# Check container status
echo "📊 Container status:"
docker ps --filter name=shift-handover-app

echo "✅ Maintenance completed"
EOF

chmod +x /opt/shift-handover-maintenance.sh

# Set up log rotation
echo "📝 Setting up log rotation..."
sudo tee /etc/logrotate.d/shift-handover > /dev/null <<EOF
/opt/shift-handover-logs/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    copytruncate
}
EOF

# Display system information
echo "📊 System Information:"
echo "OS: $(lsb_release -d | cut -f2)"
echo "Kernel: $(uname -r)"
echo "Memory: $(free -h | awk 'NR==2{printf "%.1fG used / %.1fG total (%.1f%%)", $3/1024/1024, $2/1024/1024, $3*100/$2 }')"
echo "Disk: $(df -h / | awk 'NR==2{printf "%s used / %s total (%s)", $3, $2, $5}')"
echo "Docker: $(docker --version)"

# Create a status check script
echo "🔍 Creating status check script..."
sudo tee /opt/shift-handover-status.sh > /dev/null <<'EOF'
#!/bin/bash
# Status check script for Shift Handover Application

echo "📊 Shift Handover Application Status"
echo "=================================="

# Check if container is running
if docker ps | grep -q shift-handover-app; then
    echo "✅ Container Status: Running"
    
    # Show container details
    echo "📋 Container Details:"
    docker ps --filter name=shift-handover-app --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
    
    # Show resource usage
    echo "💾 Resource Usage:"
    docker stats shift-handover-app --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}"
    
    # Test application response
    echo "🌐 Application Response:"
    if curl -f --max-time 10 http://localhost/ > /dev/null 2>&1; then
        echo "✅ HTTP: Responding"
    else
        echo "❌ HTTP: Not responding"
    fi
    
    if curl -f --max-time 10 http://localhost/login > /dev/null 2>&1; then
        echo "✅ Login page: Accessible"
    else
        echo "❌ Login page: Not accessible"
    fi
    
else
    echo "❌ Container Status: Not running"
    
    # Show recent logs if container exists but not running
    if docker ps -a | grep -q shift-handover-app; then
        echo "📋 Recent logs:"
        docker logs shift-handover-app --tail 20
    fi
fi

# Show disk usage
echo "💾 Disk Usage:"
df -h /opt

echo "=================================="
EOF

chmod +x /opt/shift-handover-status.sh

echo ""
echo "🎉 GCP VM setup completed successfully!"
echo ""
echo "📋 Next Steps:"
echo "1. Logout and login again for Docker group changes to take effect"
echo "2. Configure your SSH key for Azure DevOps access"
echo "3. Set up Azure DevOps service connections"
echo "4. Run your first deployment from Azure DevOps"
echo ""
echo "🛠️ Useful Commands:"
echo "- Check status: /opt/shift-handover-status.sh"
echo "- Run backup: /opt/shift-handover-backup.sh"
echo "- Maintenance: /opt/shift-handover-maintenance.sh"
echo "- View logs: docker logs shift-handover-app -f"
echo "- Restart app: docker restart shift-handover-app"
echo ""
echo "📁 Important Directories:"
echo "- Application data: /opt/shift-handover-data"
echo "- Uploads: /opt/shift-handover-uploads"
echo "- Logs: /opt/shift-handover-logs"
echo "- Backups: /opt/backups"
echo ""