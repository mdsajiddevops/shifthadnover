#!/bin/bash

# 🌐 HTTP-Only Setup for handover.lab.com
# Simple setup without SSL certificates - for testing domain configuration

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m' # No Color

# Default values
DOMAIN="handover.lab.com"
EMAIL=""
TEST_MODE=false

# Function to print colored output
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

print_header() {
    echo -e "${PURPLE}[HTTP-SETUP]${NC} $1"
}

# Function to show help
show_help() {
    echo -e "${PURPLE}🌐 HTTP-Only Setup for handover.lab.com${NC}"
    echo "============================================="
    echo ""
    echo "This script configures HTTP-only access for handover.lab.com"
    echo "Perfect for testing domain setup before SSL certificates"
    echo ""
    echo "Usage:"
    echo "  ./setup-http-only.sh"
    echo "  ./setup-http-only.sh --test"
    echo ""
    echo "Parameters:"
    echo "  -t, --test      Test configuration without applying changes"
    echo "  -h, --help      Show this help message"
    echo ""
    echo "What this does:"
    echo "  ✅ Configures nginx for HTTP-only access"
    echo "  ✅ Sets up handover.lab.com domain"
    echo "  ✅ No SSL certificates required"
    echo "  ✅ Works with existing docker-compose setup"
    echo ""
    echo "After setup:"
    echo "  🌐 Access: http://handover.lab.com"
    echo "  🔍 Health: http://handover.lab.com/health"
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -t|--test)
            TEST_MODE=true
            shift
            ;;
        -h|--help)
            show_help
            exit 0
            ;;
        *)
            print_error "Unknown option: $1"
            show_help
            exit 1
            ;;
    esac
done

echo -e "${PURPLE}🌐 HTTP-Only Setup for handover.lab.com${NC}"
echo "==========================================="
echo -e "${GREEN}Domain: $DOMAIN${NC}"
echo -e "${YELLOW}Mode:   HTTP Only (no SSL)${NC}"
if [ "$TEST_MODE" = true ]; then
    echo -e "${YELLOW}Test:   No changes will be applied${NC}"
fi
echo ""

# Check prerequisites
print_status "Checking prerequisites..."

# Check Docker
if ! command -v docker &> /dev/null; then
    print_error "Docker is not installed or not in PATH"
    exit 1
fi

# Check Docker Compose
if ! command -v docker-compose &> /dev/null; then
    print_error "Docker Compose is not installed or not in PATH"
    exit 1
fi

print_success "Docker and Docker Compose are available"

# Step 1: Create HTTP-only environment configuration
print_header "Creating HTTP-only configuration..."

if [ "$TEST_MODE" = false ]; then
    cat > .env.domain << EOF
# 🌐 HTTP-Only Domain Setup Configuration for handover.lab.com
DOMAIN_NAME=$DOMAIN
EMAIL=admin@epam.com
FLASK_ENV=production
FLASK_DEBUG=0
SSL_ENABLED=false
HTTP_PORT=80

# EPAM specific settings
ORGANIZATION=EPAM
ENVIRONMENT=lab
SERVICE_NAME=handover

# Network settings
EXTERNAL_IP=35.200.202.18
INTERNAL_PORT=5000

# Security settings (HTTP only)
ENABLE_RATE_LIMITING=true
ENABLE_SECURITY_HEADERS=true
ENABLE_ACCESS_LOGS=true
FORCE_HTTPS=false
EOF

    print_success "Created .env.domain with HTTP-only settings"
else
    print_status "TEST MODE: Would create .env.domain configuration"
fi

# Step 2: Create HTTP-only nginx configuration
print_header "Creating nginx configuration for HTTP-only access..."

if [ "$TEST_MODE" = false ]; then
    # Create nginx directories if they don't exist
    mkdir -p nginx/conf.d

    cat > nginx/conf.d/app.conf << 'EOF'
# HTTP-Only Configuration for handover.lab.com
# No SSL certificates required - for testing domain setup

# Rate limiting zones
limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
limit_req_zone $binary_remote_addr zone=login:10m rate=5r/m;
limit_req_zone $binary_remote_addr zone=general:10m rate=30r/m;

# Upstream to Flask app
upstream flask_app {
    server web:5000;
    keepalive 32;
}

# HTTP server - Main configuration (no HTTPS redirect)
server {
    listen 80;
    server_name handover.lab.com;
    
    # EPAM custom headers
    add_header X-Powered-By "EPAM-Labs-HTTP" always;
    add_header X-Environment "Development-HTTP" always;

    # Basic security headers (HTTP version)
    add_header X-Frame-Options DENY always;
    add_header X-Content-Type-Options nosniff always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;

    # Logging
    access_log /var/log/nginx/handover.lab.com.access.log;
    error_log /var/log/nginx/handover.lab.com.error.log;

    # Health check endpoint (for load balancer/testing)
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

    # Main application with rate limiting
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

    print_success "Created HTTP-only nginx configuration"
else
    print_status "TEST MODE: Would create nginx configuration"
fi

# Step 3: Stop existing services
print_status "Stopping existing services..."
if [ "$TEST_MODE" = false ]; then
    docker-compose down > /dev/null 2>&1 || true
    docker-compose -f docker-compose.prod.yml down > /dev/null 2>&1 || true
    print_success "Stopped existing services"
else
    print_status "TEST MODE: Would stop existing Docker services"
fi

# Step 4: Start services with HTTP-only configuration
print_header "Starting services with HTTP-only configuration..."
if [ "$TEST_MODE" = false ]; then
    # Use production docker-compose if available, otherwise regular
    if [ -f "docker-compose.prod.yml" ]; then
        COMPOSE_FILE="docker-compose.prod.yml"
        print_status "Using production Docker Compose configuration"
    else
        COMPOSE_FILE="docker-compose.yml"
        print_status "Using standard Docker Compose configuration"
    fi
    
    # Start services
    docker-compose -f "$COMPOSE_FILE" up -d
    
    # Wait for services to start
    sleep 15
    
    # Check if services are running
    if docker-compose -f "$COMPOSE_FILE" ps | grep -q "Up"; then
        print_success "Services started successfully"
        
        # Show service status
        echo ""
        print_status "Service Status:"
        docker-compose -f "$COMPOSE_FILE" ps
    else
        print_warning "Some services may have issues. Check logs:"
        print_status "docker-compose -f $COMPOSE_FILE logs"
    fi
else
    print_status "TEST MODE: Would start Docker services"
fi

# Step 5: Health checks and testing
print_header "Running health checks..."

if [ "$TEST_MODE" = false ]; then
    # Wait a bit for services to be fully ready
    sleep 5
    
    # Test local HTTP access
    print_status "Testing local HTTP access..."
    if curl -f -s "http://localhost:80/health" > /dev/null 2>&1; then
        print_success "Local HTTP health check passed"
    else
        print_warning "Local HTTP health check failed"
        # Try alternative port
        if curl -f -s "http://localhost:5000/health" > /dev/null 2>&1; then
            print_warning "Direct app access works on port 5000, nginx might have issues"
        fi
    fi
    
    # Test domain access (if accessible)
    print_status "Testing domain access..."
    if curl -f -s "http://$DOMAIN/health" > /dev/null 2>&1; then
        print_success "Domain HTTP health check passed"
    else
        print_warning "Domain HTTP health check failed - this is normal if domain mapping isn't configured yet"
    fi
else
    print_status "TEST MODE: Would run health checks"
fi

# Step 6: Create monitoring script
print_header "Creating monitoring script..."

if [ "$TEST_MODE" = false ]; then
    cat > monitor-http.sh << 'EOF'
#!/bin/bash

# 🌐 HTTP-Only Monitoring Script for handover.lab.com

GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}🌐 HTTP-Only Handover App Monitor${NC}"
echo "=================================="

echo -e "\n${BLUE}📊 Service Status:${NC}"
if [ -f "docker-compose.prod.yml" ]; then
    docker-compose -f docker-compose.prod.yml ps
else
    docker-compose ps
fi

echo -e "\n${BLUE}🔍 Local Health Check:${NC}"
if curl -f -s http://localhost:80/health > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Local HTTP access working${NC}"
else
    echo -e "${RED}❌ Local HTTP access failed${NC}"
fi

echo -e "\n${BLUE}🌐 Domain Health Check:${NC}"
if curl -f -s http://handover.lab.com/health > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Domain HTTP access working${NC}"
else
    echo -e "${YELLOW}⚠️  Domain access not working yet (normal if domain mapping not configured)${NC}"
fi

echo -e "\n${BLUE}📋 Recent Application Logs:${NC}"
if [ -f "docker-compose.prod.yml" ]; then
    docker-compose -f docker-compose.prod.yml logs --tail=20 web
else
    docker-compose logs --tail=20 web
fi

echo -e "\n${BLUE}🌐 Recent Nginx Logs:${NC}"
if [ -f "docker-compose.prod.yml" ]; then
    docker-compose -f docker-compose.prod.yml logs --tail=10 nginx
else
    docker-compose logs --tail=10 nginx
fi

echo -e "\n${BLUE}💾 System Resources:${NC}"
echo "Disk usage: $(df -h . | tail -1 | awk '{print $5}') used"
echo "Memory: $(free -h | grep '^Mem' | awk '{print $3"/"$2}')"
EOF

    chmod +x monitor-http.sh
    print_success "Created monitoring script: monitor-http.sh"
else
    print_status "TEST MODE: Would create monitoring script"
fi

# Final results
echo ""
print_success "🎉 HTTP-Only Setup Complete!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if [ "$TEST_MODE" = false ]; then
    echo -e "${BLUE}🌐 Application URLs (HTTP Only):${NC}"
    echo -e "   ${YELLOW}Primary:  http://$DOMAIN${NC}"
    echo -e "   ${YELLOW}Login:    http://$DOMAIN/login${NC}"
    echo -e "   ${YELLOW}Health:   http://$DOMAIN/health${NC}"
    echo -e "   ${GREEN}Local:    http://localhost/health${NC}"
    
    echo ""
    echo -e "${BLUE}🔧 Management Commands:${NC}"
    echo "   Monitor:       ./monitor-http.sh"
    echo "   Check status:  docker-compose ps"
    echo "   View logs:     docker-compose logs -f"
    echo "   Restart:       docker-compose restart"
    
    echo ""
    echo -e "${PURPLE}🌐 Domain Configuration:${NC}"
    echo "   Domain:        $DOMAIN"
    echo "   Protocol:      HTTP Only"
    echo "   SSL:           Disabled"
    echo "   Rate Limiting: Enabled"
    echo "   Access Logs:   Enabled"
    
    echo ""
    echo -e "${YELLOW}📋 Next Steps:${NC}"
    echo "1. Test local access: curl http://localhost/health"
    echo "2. Configure domain mapping: handover.lab.com → this server"
    echo "3. Test domain access: curl http://handover.lab.com/health"
    echo "4. Later add SSL: Run SSL setup script when ready"
    echo "5. Monitor: ./monitor-http.sh"
    
    echo ""
    echo -e "${BLUE}🔧 To add SSL later:${NC}"
    echo "   Run: ./setup-epam-lab.sh --email your-email@epam.com"
else
    echo -e "${YELLOW}This was a test run. To apply changes, run without --test${NC}"
fi

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if [ "$TEST_MODE" = false ]; then
    print_success "HTTP-only setup completed successfully! 🚀"
    echo ""
    echo -e "${GREEN}Your Shift Handover App is now configured for http://handover.lab.com${NC}"
    echo -e "${BLUE}Configure domain mapping to point handover.lab.com to this server${NC}"
else
    print_success "Test completed successfully! 🧪"
fi
