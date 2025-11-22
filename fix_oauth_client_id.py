#!/usr/bin/env python3
import sys
sys.path.append('/app')

from models.sso_config import SSOConfig
from app import app

def fix_client_id():
    with app.app_context():
        try:
            # Find the EPAM OAuth client_id configuration
            client_id_config = SSOConfig.query.filter_by(
                provider_type='oauth',
                config_key='client_id'
            ).filter(
                SSOConfig.provider_name.ilike('%epam%')
            ).first()
            
            if client_id_config:
                old_client_id = client_id_config.config_value
                # Update to the correct client ID
                client_id_config.config_value = 'oauth-client.epm-inbl.shift-handover-application.stage'
                client_id_config.save()
                
                print(f"Updated Client ID:")
                print(f"  Provider: {client_id_config.provider_name}")
                print(f"  From: {old_client_id}")
                print(f"  To:   {client_id_config.config_value}")
                print("✓ Client ID updated successfully")
            else:
                # Let's see what OAuth configs exist
                oauth_configs = SSOConfig.query.filter_by(provider_type='oauth').all()
                print(f"Found {len(oauth_configs)} OAuth configurations:")
                for config in oauth_configs:
                    print(f"  Provider: {config.provider_name}, Key: {config.config_key}, Value: {config.config_value}")
                
                print("\nNo EPAM OAuth client_id configuration found")
                
        except Exception as e:
            print(f"Error updating client ID: {e}")

if __name__ == "__main__":
    fix_client_id()