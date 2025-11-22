#!/bin/bash

echo "🚀 Deploying SSO Proxy Fix"
echo "=========================="

# Stop containers
echo "⏹️ Stopping containers..."
docker-compose -f docker-compose.prod.yml down

# Rebuild web container with ProxyFix changes
echo "🔨 Rebuilding web container..."
docker-compose -f docker-compose.prod.yml build web

# Start containers
echo "▶️ Starting containers..."
docker-compose -f docker-compose.prod.yml up -d

# Wait for services to be ready
echo "⏳ Waiting for services to start..."
sleep 30

# Check container status
echo "📊 Container Status:"
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

# Test endpoints
echo "🧪 Testing endpoints..."
echo "Health check:"
curl -s http://localhost/health | head -c 100
echo
echo "SSO callback endpoint:"
curl -I http://localhost/auth/sso/callback/oauth 2>/dev/null | head -n 3

echo "✅ Deployment complete!"
echo "📝 Please test SSO login at: http://35.200.202.18"
