#!/bin/bash

echo "🔧 Docker Compose SSO Network Debug"
echo "==================================="

# Navigate to app directory  
cd ~/shift_handover_app

echo "1. 📋 Docker Compose Status:"
docker-compose ps || echo "❌ Cannot get docker-compose status"

echo ""
echo "2. 🔍 Container Port Mappings:"
echo "All container ports:"
docker ps --format "table {{.Names}}\t{{.Ports}}"

echo ""
echo "Flask container ports specifically:"
docker port shift_handover_app_web_1 || echo "❌ No exposed ports on Flask container"

echo ""
echo "3. 🌐 Docker Networks:"
docker network ls
echo ""
echo "Docker compose network details:"
docker network ls | grep shift_handover_app || echo "No shift_handover_app network found"

echo ""
echo "4. 🧪 Testing Internal Flask Access:"
echo "Testing Flask health internally:"
docker exec shift_handover_app_web_1 curl -s -I "http://localhost:5000/health" --max-time 3 || echo "❌ Flask internal health check failed"

echo "Testing Flask SSO internally:"
docker exec shift_handover_app_web_1 curl -s -I "http://localhost:5000/auth/sso/initiate/oauth" --max-time 3 || echo "❌ Flask internal SSO failed"

echo ""
echo "5. 🔧 Nginx Container Check:"
NGINX_CONTAINER=$(docker ps --format "{{.Names}}" | grep -i nginx | head -1)
if [ -n "$NGINX_CONTAINER" ]; then
    echo "Found nginx container: $NGINX_CONTAINER"
    echo "Nginx container ports:"
    docker port $NGINX_CONTAINER || echo "No exposed ports on nginx container"
    
    echo "Testing nginx → Flask connection:"
    docker exec $NGINX_CONTAINER curl -s -I "http://shift_handover_app_web_1:5000/health" --max-time 3 || echo "❌ Nginx cannot reach Flask"
    
    echo "Nginx configuration:"
    docker exec $NGINX_CONTAINER cat /etc/nginx/conf.d/default.conf 2>/dev/null | head -15 || echo "Cannot read nginx config"
else
    echo "❌ No nginx container found"
    echo "Available containers:"
    docker ps --format "{{.Names}}"
fi

echo ""
echo "6. 🔍 Network Communication Test:"
echo "Can Flask reach nginx?"
if [ -n "$NGINX_CONTAINER" ]; then
    docker exec shift_handover_app_web_1 ping -c 1 $NGINX_CONTAINER 2>/dev/null && echo "✅ Flask can ping nginx" || echo "❌ Flask cannot ping nginx"
fi

echo ""
echo "7. 🧪 External vs Internal Access Test:"
echo "External access test (from outside VM):"
echo "  Expected: 302 redirect (working)"

echo "Internal access test (from VM):"
curl -s -I "http://localhost/health" --max-time 5 && echo "✅ VM can reach nginx on port 80" || echo "❌ VM cannot reach nginx on port 80"

echo "VM → External IP test:"
curl -s -I "http://35.200.202.18/health" --max-time 10 && echo "✅ VM can reach external IP" || echo "❌ VM cannot reach external IP (loopback issue)"

echo ""
echo "8. 📋 Docker Compose Configuration:"
if [ -f docker-compose.yml ]; then
    echo "Port mappings in docker-compose.yml:"
    grep -A 5 -B 2 "ports:" docker-compose.yml || echo "No port mappings found"
    
    echo ""
    echo "Network configuration in docker-compose.yml:"
    grep -A 10 -B 2 "networks:" docker-compose.yml || echo "No custom networks defined"
else
    echo "❌ No docker-compose.yml found in current directory"
fi

echo ""
echo "🎯 DIAGNOSIS RESULTS:"
echo "===================="
echo "Key findings:"
echo "• Flask container (shift_handover_app_web_1) has no public ports"
echo "• All traffic must go through nginx proxy"
echo "• External access works (302) but VM internal access fails"
echo ""
echo "🛠️ LIKELY SOLUTIONS:"
echo "1. Fix nginx container network connectivity"
echo "2. Check docker-compose network configuration"
echo "3. Verify nginx is properly forwarding to Flask"
echo "4. Test if nginx container exists and is running"
echo ""
echo "🧪 NEXT STEPS:"
echo "1. Check if nginx container is running"
echo "2. Verify nginx → Flask communication"
echo "3. Fix VM → nginx access issue"