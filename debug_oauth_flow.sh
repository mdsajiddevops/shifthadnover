#!/bin/bash

echo "Advanced SSO OAuth Debugging"
echo "============================"

# Check if containers are running
echo "Container Status:"
docker ps --format "table {{.Names}}\\t{{.Status}}\\t{{.Ports}}" | grep -E "(nginx|web|db)"
echo

# Check SSO configuration in database
echo "Current SSO Configuration:"
docker exec shift-handover-db mysql -u root -p$(docker exec shift-handover-db printenv MYSQL_ROOT_PASSWORD) shift_handover_db -e "
SELECT 
    id,
    provider_type,
    config_key,
    CASE 
        WHEN config_key IN ('client_secret', 'client_id') THEN CONCAT(LEFT(config_value, 8), '...')
        WHEN config_key LIKE '%secret%' OR config_key LIKE '%password%' THEN '[HIDDEN]'
        ELSE config_value 
    END as config_value,
    enabled 
FROM sso_config 
WHERE provider_type = 'oauth' AND enabled = 1 
ORDER BY config_key;" 2>/dev/null
echo

# Test OAuth endpoints accessibility
echo "Testing OAuth Endpoints:"
echo "1. SSO Initiate endpoint:"
curl -I "http://localhost/auth/sso/initiate/oauth" 2>/dev/null | head -n 3
echo

echo "2. SSO Callback endpoint:"
curl -I "http://localhost/auth/sso/callback/oauth" 2>/dev/null | head -n 3
echo

# Check recent application logs for OAuth flow
echo "Recent OAuth Logs (last 50 lines):"
docker logs shift-handover-web --tail=50 2>&1 | grep -i -E "(oauth|sso|redirect|callback|error|exception)" | tail -20
echo

# Test OAuth flow with verbose logging
echo "Testing OAuth Flow:"
echo "Starting OAuth test..."
curl -v -L "http://localhost/auth/sso/initiate/oauth" 2>&1 | head -20
echo

# Check nginx logs for any proxy issues
echo "Nginx Access Logs (OAuth related):"
docker logs shift-handover-nginx --tail=20 2>&1 | grep -i "sso\\|oauth\\|auth" | tail -10
echo

# Check for any SSL/TLS issues
echo "SSL/TLS Configuration:"
echo "Checking if HTTPS redirect is interfering..."
curl -I "http://localhost/auth/sso/initiate/oauth" 2>&1 | grep -i "location\\|redirect\\|https"
echo

echo "OAuth Debug Complete"
echo "If you see a 302 redirect to OAuth provider, check:"
echo "   1. OAuth app configuration in your provider console"
echo "   2. Client ID and Client Secret are correct"
echo "   3. Redirect URI is whitelisted: http://35.200.202.18/auth/sso/callback/oauth"
echo "   4. OAuth scopes are correct"
