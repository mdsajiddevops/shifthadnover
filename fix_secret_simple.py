#!/usr/bin/env python3
import sys
sys.path.append('/app')

from models.sso_config import SSOConfig
from models.models import db
from app import app

def fix_secret_simple():
    with app.app_context():
        try:
            # Find the OAuth client_secret configuration
            secret_config = SSOConfig.query.filter_by(
                provider_type='oauth',
                config_key='client_secret'
            ).first()
            
            if secret_config:
                # Set the correct client secret as plaintext
                secret_config.config_value = 'No42d8uXGSmREwmiTFVhPjDlq8QJqQzr'
                secret_config.encrypted = False
                db.session.commit()
                
                print(f"✅ Client secret fixed!")
                print(f"✅ Length: {len(secret_config.config_value)}")
                print(f"✅ Encrypted: {secret_config.encrypted}")
            else:
                print("❌ Client secret configuration not found")
                
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    fix_secret_simple()