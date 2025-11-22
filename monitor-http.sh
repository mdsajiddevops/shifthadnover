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
