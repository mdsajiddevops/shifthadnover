#!/usr/bin/env python3
import sys
sys.path.append('/app')

from models.sso_config import SSOConfig
from models.models import db
from app import app

def convert_to_plaintext():
    with app.app_context():
        try:
            # Find the OAuth client_secret configuration
            secret_config = SSOConfig.query.filter_by(
                provider_type='oauth',
                config_key='client_secret'
            ).first()
            
            if secret_config:
                print(f"Current client secret config:")
                print(f"  Encrypted: {secret_config.encrypted}")
                print(f"  Value length: {len(secret_config.config_value)}")
                
                if secret_config.encrypted:
                    # Set to plaintext temporarily
                    # You'll need to provide the actual client secret
                    print("Converting encrypted client secret to plaintext for OAuth compatibility...")
                    
                    # For now, mark as unencrypted so the OAuth can work
                    # The actual value will need to be updated with the real client secret
                    secret_config.encrypted = False
                    db.session.commit()
                    
                    print("✅ Client secret marked as plaintext")
                    print(f"⚠️  You need to update this with the actual client secret value")
                    print(f"Current value: {secret_config.config_value}")
                else:
                    print("✅ Client secret is already plaintext")
                    
        except Exception as e:
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    convert_to_plaintext()