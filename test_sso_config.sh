#!/bin/bash

echo "🔍 SSO Configuration Test"
echo "========================="

# Check Docker containers
echo "📦 Docker Container Status:"
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
echo

# Check nginx configuration
echo "🌐 Nginx Configuration Check:"
docker exec shift-handover-nginx nginx -t 2>&1
echo

# Check SSO database configuration
echo "💾 SSO Database Configuration:"
docker exec shift-handover-db mysql -u root -p$(docker exec shift-handover-db printenv MYSQL_ROOT_PASSWORD) shift_handover_db -e "
SELECT 
    provider_type,
    config_key,
    CASE 
        WHEN config_key LIKE '%secret%' OR config_key LIKE '%password%' THEN '[HIDDEN]'
        ELSE config_value 
    END as config_value,
    enabled 
FROM sso_config 
WHERE enabled = 1 
ORDER BY provider_type, config_key;" 2>/dev/null
echo

# Test redirect URI endpoint
echo "🔗 Testing SSO Callback Endpoints:"
curl -I http://localhost/auth/sso/callback/oauth 2>/dev/null | head -n 5
echo

# Check application logs for SSO issues
echo "📋 Recent Application Logs (SSO related):"
docker logs shift-handover-web --tail=20 2>&1 | grep -i "sso\|oauth\|auth" | tail -10
echo

# Test proxy headers
echo "🔧 Testing Proxy Headers:"
curl -H "X-Forwarded-Proto: http" -H "X-Forwarded-Host: 35.200.202.18" -I http://localhost/health 2>/dev/null | head -n 5
echo

echo "✅ SSO Test Complete"
