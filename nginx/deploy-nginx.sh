#!/bin/bash
# Deploy nginx configuration and start services

set -e

echo "🚀 Deploying nginx SSL configuration..."

# Check if certificates exist
if [ ! -f "/etc/nginx/ssl/fullchain.crt" ] || [ ! -f "/etc/nginx/ssl/private.key" ]; then
    echo "❌ SSL certificates not found!"
    echo "Please run convert-certificate.sh first to set up SSL certificates."
    exit 1
fi

# Backup current nginx config
echo "💾 Backing up current nginx configuration..."
sudo cp /etc/nginx/nginx.conf /etc/nginx/nginx.conf.backup.$(date +%Y%m%d_%H%M%S)

# Copy new nginx configuration
echo "📋 Installing new nginx configuration..."
sudo cp nginx-ssl.conf /etc/nginx/nginx.conf

# Test nginx configuration
echo "🧪 Testing nginx configuration..."
sudo nginx -t

if [ $? -eq 0 ]; then
    echo "✅ Nginx configuration is valid!"
    
    # Reload nginx
    echo "🔄 Reloading nginx..."
    sudo systemctl reload nginx
    
    # Enable nginx to start on boot
    echo "🔧 Enabling nginx service..."
    sudo systemctl enable nginx
    
    # Start nginx if it's not running
    sudo systemctl start nginx
    
    echo ""
    echo "✅ Nginx SSL reverse proxy is now active!"
    echo ""
    echo "🌐 Your application is now available at:"
    echo "   - https://10.82.143.226"
    echo "   - HTTP traffic will automatically redirect to HTTPS"
    echo ""
    echo "📊 Service status:"
    echo "   - Nginx: $(sudo systemctl is-active nginx)"
    echo ""
    echo "🔒 SSL Certificate info:"
    openssl x509 -in /etc/nginx/ssl/certificate.crt -text -noout | grep -E "(Subject:|Issuer:|Not Before:|Not After:)"
    
else
    echo "❌ Nginx configuration test failed!"
    echo "Please check the configuration and try again."
    exit 1
fi