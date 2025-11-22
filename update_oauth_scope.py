#!/usr/bin/env python3
import sys
sys.path.append('/app')

from models.sso_config import SSOConfig
from models.models import db
from app import app

def update_oauth_scope():
    with app.app_context():
        try:
            # Find the OAuth scope configuration
            scope_config = SSOConfig.query.filter_by(
                provider_type='oauth',
                config_key='scope'
            ).first()
            
            if scope_config:
                old_scope = scope_config.config_value
                # Update to include standard OpenID Connect scopes
                new_scope = 'openid profile email'
                
                scope_config.config_value = new_scope
                scope_config.encrypted = False
                db.session.commit()
                
                print(f"✅ OAuth scope updated:")
                print(f"  From: '{old_scope}'")
                print(f"  To:   '{new_scope}'")
                print()
                print("🔄 Please test OAuth login again")
            else:
                print("❌ OAuth scope configuration not found")
                
        except Exception as e:
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    update_oauth_scope()