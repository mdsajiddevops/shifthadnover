#!/usr/bin/env python3
"""
Fix SSO Proxy Headers Issue

This script fixes the SSO authentication issue by:
1. Adding ProxyFix middleware to properly handle X-Forwarded headers
2. Ensuring Flask gets correct host/scheme information from nginx
3. Checking redirect_uri configuration in database
4. Testing SSO endpoint accessibility

The issue is that Flask doesn't automatically trust X-Forwarded headers
from nginx, so it still thinks it's running on localhost:5000 instead
of the public IP address.
"""

import sys
import os
import tempfile
import shutil

def fix_app_py():
    """Add ProxyFix middleware to app.py"""
    app_py_path = "app.py"
    backup_path = f"app.py.backup.proxy_fix_{int(__import__('time').time())}"
    
    print("🔧 Adding ProxyFix middleware to app.py...")
    
    # Read current app.py
    with open(app_py_path, 'r') as f:
        content = f.read()
    
    # Create backup
    shutil.copy2(app_py_path, backup_path)
    print(f"📋 Created backup: {backup_path}")
    
    # Check if ProxyFix is already imported
    if 'from werkzeug.middleware.proxy_fix import ProxyFix' not in content:
        # Add ProxyFix import after other imports
        lines = content.split('\n')
        insert_index = 0
        
        # Find where to insert the import (after other imports)
        for i, line in enumerate(lines):
            if line.startswith('from flask') or line.startswith('import'):
                insert_index = i + 1
            elif line.startswith('#') or line.strip() == '':
                continue
            else:
                break
        
        # Insert ProxyFix import
        lines.insert(insert_index, 'from werkzeug.middleware.proxy_fix import ProxyFix')
        lines.insert(insert_index + 1, '')
        content = '\n'.join(lines)
        print("✅ Added ProxyFix import")
    else:
        print("✅ ProxyFix import already exists")
    
    # Check if ProxyFix is already applied
    if 'app.wsgi_app = ProxyFix' not in content:
        # Find where to add ProxyFix (after app creation but before routes)
        lines = content.split('\n')
        insert_index = -1
        
        # Look for app = Flask(__name__) or similar
        for i, line in enumerate(lines):
            if 'app = Flask(' in line:
                insert_index = i + 1
                break
        
        if insert_index == -1:
            # Look for app.config.from_object
            for i, line in enumerate(lines):
                if 'app.config.from_object(' in line:
                    insert_index = i + 1
                    break
        
        if insert_index != -1:
            # Add ProxyFix configuration
            proxy_fix_code = [
                '',
                '# Configure ProxyFix for nginx reverse proxy',
                '# This tells Flask to trust X-Forwarded headers from nginx',
                'app.wsgi_app = ProxyFix(',
                '    app.wsgi_app,',
                '    x_for=1,',
                '    x_proto=1,',
                '    x_host=1,',
                '    x_port=1',
                ')',
                ''
            ]
            
            for j, line in enumerate(proxy_fix_code):
                lines.insert(insert_index + j, line)
            
            content = '\n'.join(lines)
            print("✅ Added ProxyFix middleware configuration")
        else:
            print("❌ Could not find where to add ProxyFix middleware")
            return False
    else:
        print("✅ ProxyFix middleware already configured")
    
    # Write the updated content
    with open(app_py_path, 'w') as f:
        f.write(content)
    
    return True

def create_sso_test_script():
    """Create a test script to verify SSO configuration"""
    test_script = '''#!/bin/bash

echo "🔍 SSO Configuration Test"
echo "========================="

# Check Docker containers
echo "📦 Docker Container Status:"
docker ps --format "table {{.Names}}\\t{{.Status}}\\t{{.Ports}}"
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
docker logs shift-handover-web --tail=20 2>&1 | grep -i "sso\\|oauth\\|auth" | tail -10
echo

# Test proxy headers
echo "🔧 Testing Proxy Headers:"
curl -H "X-Forwarded-Proto: http" -H "X-Forwarded-Host: 35.200.202.18" -I http://localhost/health 2>/dev/null | head -n 5
echo

echo "✅ SSO Test Complete"
'''
    
    with open('test_sso_config.sh', 'w') as f:
        f.write(test_script)
    
    os.chmod('test_sso_config.sh', 0o755)
    print("✅ Created test_sso_config.sh script")

def create_deployment_script():
    """Create deployment script to apply fixes"""
    deploy_script = '''#!/bin/bash

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
docker ps --format "table {{.Names}}\\t{{.Status}}\\t{{.Ports}}"

# Test endpoints
echo "🧪 Testing endpoints..."
echo "Health check:"
curl -s http://localhost/health | head -c 100
echo
echo "SSO callback endpoint:"
curl -I http://localhost/auth/sso/callback/oauth 2>/dev/null | head -n 3

echo "✅ Deployment complete!"
echo "📝 Please test SSO login at: http://35.200.202.18"
'''
    
    with open('deploy_sso_fix.sh', 'w') as f:
        f.write(deploy_script)
    
    os.chmod('deploy_sso_fix.sh', 0o755)
    print("✅ Created deploy_sso_fix.sh script")

def main():
    print("🔧 SSO Proxy Headers Fix")
    print("=" * 50)
    
    # Check if we're in the right directory
    if not os.path.exists('app.py'):
        print("❌ app.py not found. Please run this script from the project root.")
        sys.exit(1)
    
    # Apply fixes
    if fix_app_py():
        print("✅ Successfully updated app.py with ProxyFix middleware")
    else:
        print("❌ Failed to update app.py")
        sys.exit(1)
    
    # Create test and deployment scripts
    create_sso_test_script()
    create_deployment_script()
    
    print("\n🎯 Next Steps:")
    print("1. Run: ./deploy_sso_fix.sh (to deploy the fix)")
    print("2. Run: ./test_sso_config.sh (to test configuration)")
    print("3. Test SSO login at: http://35.200.202.18")
    print("\n💡 The ProxyFix middleware will now properly handle nginx proxy headers")
    print("   so Flask will know the correct host and protocol for OAuth redirects.")

if __name__ == '__main__':
    main()