#!/bin/bash

echo "🔧 Fix nginx → Flask connectivity for SSO"
echo "========================================"

cd ~/shift_handover_app

echo "1. 📋 Current Issue:"
echo "✅ nginx can reach Flask via IP (172.28.0.3:5000)"
echo "❌ SSO returns 400 Bad Request - likely Host header issue"
echo "❌ DNS resolution for 'web' alias not working"

echo ""
echo "2. 🛠️ Creating fixed nginx configuration..."

# Backup current config
docker exec shift_handover_app_nginx_1 cp /etc/nginx/conf.d/ip-access.conf /etc/nginx/conf.d/ip-access.conf.backup

# Create new config with direct IP and proper headers
cat > nginx_sso_fix.conf << 'EOF'
# Fixed HTTP Configuration for SSO with Direct IP
# Maps port 80 → Flask app on IP 172.28.0.3:5000

upstream flask_app {
    server 172.28.0.3:5000;
    keepalive 32;
}

# HTTP server for IP access (35.200.202.18)
server {
    listen 80 default_server;
    server_name _;  # Accept any server name/IP

    # Health check endpoint
    location /health {
        proxy_pass http://flask_app/health;
        proxy_set_header Host $http_host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Forwarded-Host $host;
        proxy_set_header X-Forwarded-Port $server_port;
        access_log off;
    }

    # SSO specific configuration with proper headers for ProxyFix
    location /auth/sso/ {
        proxy_pass http://flask_app;
        proxy_set_header Host $http_host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Forwarded-Host $host;
        proxy_set_header X-Forwarded-Port $server_port;

        # Timeout settings for SSO (longer for OAuth redirects)
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;

        # Buffer settings
        proxy_buffering on;
        proxy_buffer_size 4k;
        proxy_buffers 8 4k;
        proxy_busy_buffers_size 8k;
    }

    # Main application - proxy all other requests to Flask app
    location / {
        proxy_pass http://flask_app;
        proxy_set_header Host $http_host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Forwarded-Host $host;
        proxy_set_header X-Forwarded-Port $server_port;

        # Timeout settings
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;

        # Buffer settings
        proxy_buffering on;
        proxy_buffer_size 4k;
        proxy_buffers 8 4k;
        proxy_busy_buffers_size 8k;
    }
}
EOF

echo "3. 🔄 Applying fixed nginx configuration..."
docker cp nginx_sso_fix.conf shift_handover_app_nginx_1:/etc/nginx/conf.d/ip-access.conf

echo "4. 🧪 Testing nginx configuration..."
docker exec shift_handover_app_nginx_1 nginx -t && echo "✅ Nginx config is valid" || echo "❌ Nginx config is invalid"

echo "5. 🔄 Reloading nginx..."
docker exec shift_handover_app_nginx_1 nginx -s reload && echo "✅ Nginx reloaded successfully" || echo "❌ Nginx reload failed"

echo ""
echo "6. 🧪 Testing fixed connectivity..."
echo "Testing health endpoint:"
curl -s -I "http://localhost:80/health" --max-time 5 && echo "✅ Health endpoint works" || echo "❌ Health endpoint failed"

echo ""
echo "Testing SSO endpoint:"
curl -s -I "http://localhost:80/auth/sso/initiate/oauth" --max-time 5 && echo "✅ SSO endpoint works" || echo "❌ SSO endpoint failed"

echo ""
echo "Testing external access:"
curl -s -I "http://35.200.202.18/auth/sso/initiate/oauth" --max-time 10 && echo "✅ External SSO works" || echo "❌ External SSO failed"

echo ""
echo "🎉 nginx → Flask connectivity fix completed!"
echo "==========================================="
echo ""
echo "🧪 Test your SSO now:"
echo "1. Go to: http://35.200.202.18/login"
echo "2. Click SSO button"
echo "3. Should redirect to EPAM Keycloak correctly"
echo ""
echo "🔧 If still not working:"
echo "1. Check Flask ProxyFix middleware is working"
echo "2. Verify EPAM OAuth client configuration"
echo "3. Check application logs: docker logs shift_handover_app_web_1"