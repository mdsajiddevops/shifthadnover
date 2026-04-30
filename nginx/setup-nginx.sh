#!/bin/bash
# Setup script for nginx reverse proxy with SSL

set -e

echo "🚀 Setting up nginx reverse proxy for Shift Handover application..."

# Update system packages
echo "📦 Updating system packages..."
sudo apt update
sudo apt upgrade -y

# Install nginx
echo "🌐 Installing nginx..."
sudo apt install nginx -y

# Install SSL tools
echo "🔒 Installing SSL tools..."
sudo apt install openssl -y

# Stop nginx temporarily for configuration
echo "⏹️ Stopping nginx for configuration..."
sudo systemctl stop nginx

# Create SSL directory
echo "📁 Creating SSL directory..."
sudo mkdir -p /etc/nginx/ssl
sudo chmod 700 /etc/nginx/ssl

# Backup original nginx config
echo "💾 Backing up original nginx configuration..."
sudo cp /etc/nginx/nginx.conf /etc/nginx/nginx.conf.backup

echo "✅ Nginx installation complete!"
echo ""
echo "Next steps:"
echo "1. Upload your PFX certificate to the VM"
echo "2. Run the convert-certificate.sh script to convert PFX to PEM format"
echo "3. Copy the nginx configuration files"
echo "4. Update your application's SSO redirect URLs"
echo "5. Start nginx"
echo ""
echo "Nginx status: $(sudo systemctl is-active nginx)"