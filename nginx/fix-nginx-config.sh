#!/bin/bash
# Quick fix for nginx upstream configuration

set -e

echo "🔧 Fixing nginx upstream configuration..."

# Update the nginx configuration file
sudo cp nginx-ssl.conf /etc/nginx/nginx.conf

# Test nginx configuration
echo "🧪 Testing nginx configuration..."
sudo nginx -t

if [ $? -eq 0 ]; then
    echo "✅ Nginx configuration is valid!"
    
    # Reload nginx
    echo "🔄 Reloading nginx..."
    sudo systemctl reload nginx
    
    # Enable and start nginx
    sudo systemctl enable nginx
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
    echo "   - Port 80: $(sudo netstat -tlnp | grep ':80 ' || echo 'Not listening')"
    echo "   - Port 443: $(sudo netstat -tlnp | grep ':443 ' || echo 'Not listening')"
    
else
    echo "❌ Nginx configuration test failed!"
    echo "Please check the configuration and try again."
    exit 1
fi