#!/usr/bin/env python3
import sys
sys.path.append('/app')

from models.sso_config import SSOConfig
from app import app

def fix_client_id():
    with app.app_context():
        try:
            # Find the EPAM OAuth configuration
            epam_config = SSOConfig.query.filter_by(
                provider_type='oauth',
                provider_name='EPAM'
            ).first()
            
            if epam_config:
                old_client_id = epam_config.client_id
                # Update to the correct client ID
                epam_config.client_id = 'oauth-client.epm-inbl.shift-handover-application.stage'
                epam_config.save()
                
                print(f"Updated Client ID:")
                print(f"  From: {old_client_id}")
                print(f"  To:   {epam_config.client_id}")
                print("✓ Client ID updated successfully")
            else:
                print("No EPAM OAuth configuration found")
                
        except Exception as e:
            print(f"Error updating client ID: {e}")

if __name__ == "__main__":
    fix_client_id()