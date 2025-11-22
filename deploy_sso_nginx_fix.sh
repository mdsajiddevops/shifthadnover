#!/bin/bash

echo "🔧 Fixing SSO with nginx ProxyFix"
echo "=================================="

# Step 1: Copy updated app.py with ProxyFix
echo "1. Deploying ProxyFix middleware fix..."
docker cp app.py shift_handover_app_web_1:/app/

# Step 2: Copy SSO diagnostic tool
echo "2. Copying SSO diagnostic tool..."
docker cp fix_sso_nginx.py shift_handover_app_web_1:/app/

# Step 3: Run SSO diagnostic
echo "3. Running SSO configuration check..."
docker exec shift_handover_app_web_1 python fix_sso_nginx.py

# Step 4: Restart container to apply ProxyFix
echo "4. Restarting container to apply ProxyFix middleware..."
docker restart shift_handover_app_web_1

echo "5. Waiting for container to restart..."
sleep 15

# Step 5: Check container status
echo "6. Checking container status..."
docker ps | grep shift_handover_app_web_1

echo ""
echo "🎉 SSO + nginx ProxyFix deployment completed!"
echo ""
echo "📋 What was fixed:"
echo "  ✅ Added ProxyFix middleware to handle nginx proxy headers"
echo "  ✅ Flask will now construct correct URLs behind nginx proxy"  
echo "  ✅ SSO redirect URIs will use http://35.200.202.18 instead of localhost:5000"
echo ""
echo "🧪 Test the fix:"
echo "  1. Go to: http://35.200.202.18/login"
echo "  2. Click 'Sign in with SSO' or similar SSO button"
echo "  3. Should redirect to OAuth provider with correct redirect_uri"
echo ""
echo "🔧 If SSO still doesn't work:"
echo "  1. Check SSO config: docker exec shift-handover-web python fix_sso_nginx.py"
echo "  2. Update OAuth provider console with new redirect URI"
echo "  3. Verify OAuth client ID and secret are correct"
