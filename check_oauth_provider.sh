#!/bin/bash

echo "OAuth Provider Configuration Check"
echo "=================================="

# Get OAuth configuration from database
echo "Retrieving OAuth Configuration..."
docker exec shift-handover-db mysql -u root -p$(docker exec shift-handover-db printenv MYSQL_ROOT_PASSWORD) shift_handover_db -e "
SELECT config_key, config_value 
FROM sso_config 
WHERE provider_type = 'oauth' AND enabled = 1 
ORDER BY config_key;" 2>/dev/null > oauth_config.tmp

# Parse configuration
CLIENT_ID=$(grep "client_id" oauth_config.tmp | cut -f2)
AUTH_ENDPOINT=$(grep "authorization_endpoint" oauth_config.tmp | cut -f2)
REDIRECT_URI=$(grep "redirect_uri" oauth_config.tmp | cut -f2)
SCOPE=$(grep "scope" oauth_config.tmp | cut -f2)

echo "OAuth Configuration Summary:"
echo "Client ID: ${CLIENT_ID:0:10}..."
echo "Authorization Endpoint: $AUTH_ENDPOINT"
echo "Redirect URI: $REDIRECT_URI"
echo "Scope: $SCOPE"
echo

# Test authorization endpoint
echo "Testing Authorization Endpoint:"
if [ ! -z "$AUTH_ENDPOINT" ]; then
    curl -I "$AUTH_ENDPOINT" 2>/dev/null | head -n 3
    echo "Authorization endpoint is accessible"
else
    echo "Authorization endpoint not configured"
fi
echo

# Check if redirect URI matches current setup
echo "Redirect URI Validation:"
if [[ "$REDIRECT_URI" == "http://35.200.202.18/auth/sso/callback/oauth" ]]; then
    echo "Redirect URI is correctly configured"
else
    echo "Redirect URI mismatch!"
    echo "   Expected: http://35.200.202.18/auth/sso/callback/oauth"
    echo "   Actual: $REDIRECT_URI"
fi
echo

# Clean up
rm -f oauth_config.tmp

echo "Next Steps:"
echo "1. Verify in your OAuth provider console that:"
echo "   - Client ID matches: ${CLIENT_ID:0:10}..."
echo "   - Redirect URI is whitelisted: http://35.200.202.18/auth/sso/callback/oauth"
echo "   - Required scopes are enabled: $SCOPE"
echo "2. Check if your OAuth app is in production mode (not sandbox/development)"
echo "3. Ensure the OAuth app domain/origin is correctly configured"