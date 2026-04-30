#!/bin/bash
# Fix SSO redirect URIs for HTTPS access

set -e

echo "🔧 Updating SSO redirect URIs for HTTPS access..."

# Get the container name for the web application
WEB_CONTAINER=$(docker ps --filter "name=shift-web" --format "{{.Names}}" | head -1)

if [ -z "$WEB_CONTAINER" ]; then
    echo "❌ Could not find shift-web container!"
    echo "Please make sure your Docker Compose application is running."
    exit 1
fi

echo "📡 Found web container: $WEB_CONTAINER"

# Update the redirect URI in the database
echo "🔄 Updating OAuth redirect URI from HTTP to HTTPS..."

# Execute the fix inside the container
docker exec -it $WEB_CONTAINER python -c "
import sys
sys.path.append('/app')

from models.sso_config import SSOConfig
from models.models import db
from flask import Flask

# Create minimal Flask app
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:rootpassword@db/shift_handover'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

with app.app_context():
    try:
        # Get current redirect URI
        redirect_config = SSOConfig.query.filter_by(
            provider_type='oauth',
            config_key='redirect_uri'
        ).first()
        
        if redirect_config:
            current_uri = redirect_config.config_value
            print(f'Current redirect URI: {current_uri}')
            
            # Update to HTTPS without port
            if 'http://' in current_uri or ':5000' in current_uri:
                new_uri = 'https://10.82.143.226/auth/sso/callback/oauth'
                redirect_config.config_value = new_uri
                db.session.commit()
                print(f'✅ Updated redirect URI to: {new_uri}')
            else:
                print('ℹ️  Redirect URI already correct')
        else:
            print('❌ No redirect URI configuration found')
            
    except Exception as e:
        print(f'❌ Error: {str(e)}')
"

echo ""
echo "✅ SSO configuration updated!"
echo ""
echo "🔄 Please restart your application container to apply changes:"
echo "   docker-compose restart shift-web"
echo ""
echo "🌐 Your SSO login should now work with:"
echo "   https://10.82.143.226"