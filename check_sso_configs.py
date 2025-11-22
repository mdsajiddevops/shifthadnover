#!/usr/bin/env python3
import sys
sys.path.append('/app')

from models.sso_config import SSOConfig
from app import app

def check_sso_configs():
    with app.app_context():
        try:
            # Get all SSO configurations
            all_configs = SSOConfig.query.all()
            
            print(f"Found {len(all_configs)} SSO configuration(s):")
            
            for config in all_configs:
                print(f"\n--- Configuration {config.id} ---")
                print(f"Provider Type: {config.provider_type}")
                print(f"Provider Name: {config.provider_name}")
                print(f"Client ID: {config.client_id}")
                print(f"Is Active: {config.is_active}")
                
            # Specifically look for OAuth configurations
            oauth_configs = SSOConfig.query.filter_by(provider_type='oauth').all()
            print(f"\n{len(oauth_configs)} OAuth configuration(s) found")
            
            # Look for EPAM configurations (case insensitive)
            epam_configs = SSOConfig.query.filter(
                SSOConfig.provider_name.ilike('%epam%')
            ).all()
            print(f"{len(epam_configs)} EPAM configuration(s) found")
                
        except Exception as e:
            print(f"Error checking configurations: {e}")

if __name__ == "__main__":
    check_sso_configs()