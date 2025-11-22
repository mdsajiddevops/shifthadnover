#!/usr/bin/env python3
import sys
sys.path.append('/app')

from models.sso_config import SSOConfig
from models.models import db
from app import app

def update_client_secret_direct():
    with app.app_context():
        try:
            print("🔧 Direct Client Secret Update Tool")
            print("This will update the OAuth client secret as plaintext")
            print()
            
            # Get the current client secret config
            secret_config = SSOConfig.query.filter_by(
                provider_type='oauth',
                config_key='client_secret'
            ).first()
            
            if secret_config:
                print(f"Current config found:")
                print(f"  Encrypted: {secret_config.encrypted}")
                print(f"  Value length: {len(secret_config.config_value)}")
                print(f"  Starts with: {secret_config.config_value[:10]}...")
                print()
                
                # Get the new client secret from stdin
                new_secret = input("Enter the actual client secret: ").strip()
                
                if new_secret:
                    # Update with plaintext
                    secret_config.config_value = new_secret
                    secret_config.encrypted = False
                    db.session.commit()
                    
                    print("✅ Client secret updated successfully!")
                    print(f"✅ New length: {len(new_secret)}")
                    print(f"✅ Encrypted: {secret_config.encrypted}")
                    print()
                    print("🔄 Please test OAuth login now")
                else:
                    print("❌ No client secret provided")
            else:
                print("❌ Client secret configuration not found")
                
        except Exception as e:
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    update_client_secret_direct()