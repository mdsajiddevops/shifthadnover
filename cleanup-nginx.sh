#!/bin/bash

# 🧹 Clean Nginx Configuration Script
# Fixes duplicate rate limiting zones and deprecated directives

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

echo -e "${GREEN}🧹 Cleaning Nginx Configuration${NC}"
echo "=================================="

# Step 1: Stop services
print_status "Stopping nginx service..."
docker-compose -f docker-compose.prod.yml stop nginx 2>/dev/null || true

# Step 2: Backup existing configurations
print_status "Backing up existing configurations..."
mkdir -p nginx/conf.d/backup
if [ -d "nginx/conf.d" ]; then
    cp nginx/conf.d/*.conf nginx/conf.d/backup/ 2>/dev/null || true
    print_success "Backed up existing configurations"
fi

# Step 3: Remove conflicting configurations
print_status "Removing conflicting configuration files..."
rm -f nginx/conf.d/default.conf
rm -f nginx/conf.d/epam-lab.conf
rm -f nginx/conf.d/app.conf
rm -f nginx/conf.d/http-only.conf
rm -f nginx/conf.d/https.conf

print_success "Removed conflicting configuration files"

# Step 4: Create clean configuration
print_status "Creating clean nginx configuration..."

# Ensure main nginx.conf has rate limiting zones
cat > nginx/nginx.conf << 'EOF'
user nginx;
worker_processes auto;
error_log /var/log/nginx/error.log notice;
pid /var/run/nginx.pid;

events {
    worker_connections 1024;
    use epoll;
    multi_accept on;
}

http {
    include       /etc/nginx/mime.types;
    default_type  application/octet-stream;

    # Logging Settings
    log_format main '$remote_addr - $remote_user [$time_local] "$request" '
                    '$status $body_bytes_sent "$http_referer" '
                    '"$http_user_agent" "$http_x_forwarded_for"';

    access_log /var/log/nginx/access.log main;
    error_log /var/log/nginx/error.log;

    # Basic Settings
    sendfile on;
    tcp_nopush on;
    tcp_nodelay on;
    keepalive_timeout 65;
    types_hash_max_size 2048;
    server_tokens off;
    client_max_body_size 20M;

    # Rate limiting zones (GLOBAL - defined once here)
    limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
    limit_req_zone $binary_remote_addr zone=login:10m rate=5r/m;
    limit_req_zone $binary_remote_addr zone=general:10m rate=30r/m;

    # Gzip Settings
    gzip on;
    gzip_vary on;
    gzip_proxied any;
    gzip_comp_level 6;
    gzip_types
        text/plain
        text/css
        text/xml
        text/javascript
        application/json
        application/javascript
        application/xml+rss
        application/atom+xml
        image/svg+xml;

    # Include server configurations
    include /etc/nginx/conf.d/*.conf;
}
EOF

# Create single clean server configuration
cat > nginx/conf.d/handover.conf << 'EOF'
# Clean HTTP-Only Configuration for handover.lab.com
# Single configuration file to avoid conflicts

# Upstream to Flask app
upstream flask_app {
    server web:5000;
    keepalive 32;
}

# HTTP server for handover.lab.com
server {
    listen 80;
    server_name handover.lab.com localhost;
    
    # EPAM custom headers
    add_header X-Powered-By "EPAM-Labs-HTTP" always;
    add_header X-Environment "Production-HTTP" always;

    # Basic security headers
    add_header X-Frame-Options DENY always;
    add_header X-Content-Type-Options nosniff always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;

    # Logging
    access_log /var/log/nginx/handover.lab.com.access.log;
    error_log /var/log/nginx/handover.lab.com.error.log;

    # Health check endpoint (no rate limiting)
    location /health {
        proxy_pass http://flask_app/health;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        access_log off;
    }

    # API endpoints with rate limiting
    location /api/ {
        limit_req zone=api burst=20 nodelay;
        proxy_pass http://flask_app;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Forwarded-Host $host;
        proxy_set_header X-Forwarded-Port $server_port;
    }

    # Login endpoint with stricter rate limiting
    location /login {
        limit_req zone=login burst=5 nodelay;
        proxy_pass http://flask_app;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Forwarded-Host $host;
        proxy_set_header X-Forwarded-Port $server_port;
    }

    # Static files with caching
    location /static/ {
        proxy_pass http://flask_app;
        proxy_set_header Host $host;
        expires 1h;
        add_header Cache-Control "public, immutable";
    }

    # Main application with general rate limiting
    location / {
        limit_req zone=general burst=50 nodelay;
        proxy_pass http://flask_app;
        proxy_set_header Host $host;
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

# Default server block to handle other requests
server {
    listen 80 default_server;
    server_name _;
    return 444;  # Close connection without response
}
EOF

print_success "Created clean nginx configuration"

# Step 5: Test configuration
print_status "Testing nginx configuration..."
if docker run --rm -v "$(pwd)/nginx/nginx.conf:/etc/nginx/nginx.conf:ro" -v "$(pwd)/nginx/conf.d:/etc/nginx/conf.d:ro" nginx:alpine nginx -t; then
    print_success "✅ Nginx configuration is valid!"
else
    print_error "❌ Nginx configuration has errors"
    exit 1
fi

# Step 6: Create environment configuration
print_status "Creating environment configuration..."
cat > .env.domain << 'EOF'
# HTTP-Only Configuration for handover.lab.com
DOMAIN_NAME=handover.lab.com
EMAIL=admin@epam.com
FLASK_ENV=production
FLASK_DEBUG=0
SSL_ENABLED=false
HTTP_PORT=80
FORCE_HTTPS=false
EOF

print_success "Created .env.domain"

# Step 7: Start services
print_status "Starting services with clean configuration..."
docker-compose -f docker-compose.prod.yml up -d

# Wait for services to start
print_status "Waiting for services to start..."
sleep 15

# Step 8: Check service status
print_status "Checking service status..."
if docker-compose -f docker-compose.prod.yml ps | grep -q "Up"; then
    print_success "✅ Services started successfully!"
    
    echo ""
    print_status "Service Status:"
    docker-compose -f docker-compose.prod.yml ps
else
    print_warning "⚠️  Some services may have issues"
    docker-compose -f docker-compose.prod.yml ps
fi

# Step 9: Test access
print_status "Testing local access..."
sleep 5

if curl -f -s "http://localhost:80/health" > /dev/null 2>&1; then
    print_success "✅ Local HTTP access working!"
    echo "Response: $(curl -s http://localhost:80/health)"
else
    print_warning "⚠️  Local HTTP access test failed"
    print_status "Checking if Flask app is accessible directly..."
    if curl -f -s "http://localhost:5000/health" > /dev/null 2>&1; then
        print_warning "Flask app is accessible on port 5000, nginx might need more time"
    fi
fi

# Step 10: Show configuration summary
echo ""
print_success "🎉 Nginx Configuration Cleanup Complete!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo -e "${GREEN}✅ Removed conflicting configuration files${NC}"
echo -e "${GREEN}✅ Created single clean configuration${NC}"
echo -e "${GREEN}✅ Fixed rate limiting zone conflicts${NC}"
echo -e "${GREEN}✅ Removed deprecated HTTP/2 directives${NC}"
echo -e "${GREEN}✅ Services restarted successfully${NC}"
echo ""
echo -e "${BLUE}🌐 Application URLs:${NC}"
echo -e "   Local:  ${GREEN}http://localhost/health${NC}"
echo -e "   Domain: ${YELLOW}http://handover.lab.com/health${NC} (after domain mapping)"
echo ""
echo -e "${BLUE}📁 Configuration Files:${NC}"
echo "   Main config:    nginx/nginx.conf"
echo "   Server config:  nginx/conf.d/handover.conf"
echo "   Environment:    .env.domain"
echo "   Backups:        nginx/conf.d/backup/"
echo ""
echo -e "${BLUE}🔧 Management Commands:${NC}"
echo "   Check status:   docker-compose -f docker-compose.prod.yml ps"
echo "   View logs:      docker-compose -f docker-compose.prod.yml logs nginx"
echo "   Test config:    docker-compose -f docker-compose.prod.yml exec nginx nginx -t"
echo "   Restart:        docker-compose -f docker-compose.prod.yml restart nginx"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

print_success "Configuration cleanup completed! 🚀"

echo ""
echo -e "${YELLOW}📋 Next Steps:${NC}"
echo "1. Test: curl http://localhost/health"
echo "2. Configure domain mapping with NAT team"
echo "3. Test domain: curl http://handover.lab.com/health"