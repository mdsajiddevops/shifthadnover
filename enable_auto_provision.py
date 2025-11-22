#!/usr/bin/env python3
import sys
sys.path.append('/app')

from models.sso_config import SSOConfig
from models.models import db
from app import app

def enable_auto_provision():
    with app.app_context():
        try:
            # Find the OAuth auto_provision configuration
            auto_provision_config = SSOConfig.query.filter_by(
                provider_type='oauth',
                config_key='auto_provision'
            ).first()
            
            if auto_provision_config:
                old_value = auto_provision_config.config_value
                # Enable auto-provisioning
                auto_provision_config.config_value = 'true'
                auto_provision_config.encrypted = False
                db.session.commit()
                
                print(f"✅ Auto-provisioning updated:")
                print(f"  From: '{old_value}'")
                print(f"  To:   'true'")
                
                # Also check the default role
                default_role_config = SSOConfig.query.filter_by(
                    provider_type='oauth',
                    config_key='default_role'
                ).first()
                
                if default_role_config:
                    print(f"✅ Default role: '{default_role_config.config_value}'")
                else:
                    print("⚠️ No default role configured")
                
                print()
                print("🔄 Please test OAuth login again - users will now be auto-created")
            else:
                print("❌ Auto-provision configuration not found")
                
        except Exception as e:
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    enable_auto_provision()