#!/usr/bin/env python3
import sys
sys.path.append('/app')

from models.sso_config import SSOConfig
from models.models import db
from app import app

def disable_encryption():
    with app.app_context():
        try:
            # Find all OAuth configurations and disable encryption
            oauth_configs = SSOConfig.query.filter_by(provider_type='oauth').all()
            
            updated_count = 0
            for config in oauth_configs:
                if config.encrypted:
                    print(f"Disabling encryption for: {config.config_key}")
                    config.encrypted = False
                    updated_count += 1
            
            if updated_count > 0:
                db.session.commit()
                print(f"✅ Disabled encryption for {updated_count} OAuth configuration(s)")
                print("🔄 Now you can update the client secret via web interface")
            else:
                print("ℹ️ All OAuth configurations are already unencrypted")
                
            # Show current OAuth configs
            print("\n📋 Current OAuth configurations:")
            for config in oauth_configs:
                print(f"  {config.config_key}: encrypted={config.encrypted}, length={len(config.config_value) if config.config_value else 0}")
                
        except Exception as e:
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    disable_encryption()