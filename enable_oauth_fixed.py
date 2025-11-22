#!/usr/bin/env python3
import sys
sys.path.append('/app')

from models.sso_config import SSOConfig
from models.models import db
from app import app

def enable_oauth_config():
    with app.app_context():
        try:
            # Find the OAuth enabled configuration
            enabled_config = SSOConfig.query.filter_by(
                provider_type='oauth',
                config_key='enabled'
            ).first()
            
            if enabled_config:
                old_value = enabled_config.config_value
                enabled_config.config_value = 'true'  # Enable OAuth
                db.session.commit()
                
                print(f"Updated OAuth enabled status:")
                print(f"  From: {old_value}")
                print(f"  To:   {enabled_config.config_value}")
                print("✓ OAuth configuration enabled successfully")
                
                # Also verify the client ID is correct
                client_id_config = SSOConfig.query.filter_by(
                    provider_type='oauth',
                    config_key='client_id'
                ).first()
                
                if client_id_config:
                    print(f"\n✓ Current Client ID: {client_id_config.config_value}")
                    if client_id_config.config_value != 'oauth-client.epm-inbl.shift-handover-application.stage':
                        print("⚠️ Client ID needs to be updated!")
                    else:
                        print("✓ Client ID is correct")
                        
                # Restart the web service to reload configuration
                print("\n🔄 Restarting web service to reload configuration...")
                
            else:
                print("No OAuth enabled configuration found")
                
        except Exception as e:
            print(f"Error enabling OAuth: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    enable_oauth_config()