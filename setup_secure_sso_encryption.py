#!/usr/bin/env python3
import sys
sys.path.append('/app')

from models.sso_config import SSOConfig
from models.models import db
from app import app
import os
from cryptography.fernet import Fernet

def setup_secure_sso_encryption():
    with app.app_context():
        try:
            # Step 1: Set a persistent encryption key
            # Generate a secure key for production use
            persistent_key = Fernet.generate_key().decode()
            os.environ['SSO_ENCRYPTION_KEY'] = persistent_key
            
            print("🔐 Setting up secure SSO encryption...")
            print(f"🔑 Generated persistent encryption key: {persistent_key}")
            print("⚠️  IMPORTANT: Store this key securely in your environment!")
            print("   Add this to your docker-compose.yml or environment:")
            print(f"   SSO_ENCRYPTION_KEY={persistent_key}")
            print()
            
            # Step 2: Re-encrypt all sensitive SSO configuration values
            sensitive_configs = [
                ('client_secret', 'No42d8uXGSmREwmiTFVhPjDlq8QJqQzr'),  # Current working client secret
                ('client_id', 'oauth-client.epm-inbl.shift-handover-application.stage')  # Client ID
            ]
            
            for config_key, correct_value in sensitive_configs:
                config = SSOConfig.query.filter_by(
                    provider_type='oauth',
                    config_key=config_key
                ).first()
                
                if config:
                    # Set the correct value and mark as encrypted
                    config.config_value = correct_value
                    config.encrypted = False  # Set to plaintext first
                    db.session.commit()
                    
                    # Now encrypt it using the SSOConfig's encryption method
                    encrypted_value = SSOConfig._encrypt_value(correct_value)
                    config.config_value = encrypted_value
                    config.encrypted = True
                    db.session.commit()
                    
                    print(f"✅ {config_key}: Encrypted and secured")
                    print(f"   Length: {len(encrypted_value)} characters")
                else:
                    print(f"❌ {config_key}: Configuration not found")
            
            # Step 3: Verify encryption/decryption works
            print("\n🔍 Verifying encryption system...")
            oauth_config = SSOConfig.get_provider_config('oauth')
            
            client_secret = oauth_config.get('client_secret')
            client_id = oauth_config.get('client_id')
            
            if client_secret and len(client_secret) == 32:
                print(f"✅ Client secret: Decrypted successfully (length: {len(client_secret)})")
                print(f"   Starts with: {client_secret[:5]}...")
            else:
                print(f"❌ Client secret: Decryption issue (length: {len(client_secret) if client_secret else 0})")
                
            if client_id and 'oauth-client.epm-inbl' in client_id:
                print(f"✅ Client ID: Decrypted successfully")
                print(f"   Value: {client_id}")
            else:
                print(f"❌ Client ID: Decryption issue")
            
            # Step 4: Show encrypted values in database (for verification)
            print("\n📊 Database encrypted values:")
            raw_configs = SSOConfig.query.filter_by(provider_type='oauth').all()
            for config in raw_configs:
                if config.config_key in ['client_secret', 'client_id']:
                    print(f"   {config.config_key}: {config.config_value[:20]}... (encrypted: {config.encrypted})")
                    
        except Exception as e:
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    setup_secure_sso_encryption()