#!/usr/bin/env python3
"""
SSO Diagnosis and Fix Tool
Diagnoses SSO configuration issues and applies fixes for nginx proxy setup
"""

import sqlite3
import os
import sys

def check_sso_config():
    """Check current SSO configuration"""
    db_path = 'data/app.db'
    
    if not os.path.exists(db_path):
        print("❌ Database not found at data/app.db")
        return False
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if sso_config table exists
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='sso_config'
        """)
        
        if not cursor.fetchone():
            print("❌ sso_config table not found")
            return False
        
        # Get all SSO configurations
        cursor.execute("""
            SELECT id, provider_name, provider_type, config_key, config_value, enabled
            FROM sso_config 
            ORDER BY provider_name, config_key
        """)
        
        configs = cursor.fetchall()
        
        if not configs:
            print("❌ No SSO configurations found")
            return False
        
        print("📋 Current SSO Configuration:")
        print("-" * 80)
        
        current_provider = None
        redirect_uri_found = False
        old_redirect_uris = []
        
        for config in configs:
            id_val, provider_name, provider_type, config_key, config_value, enabled = config
            
            if current_provider != provider_name:
                if current_provider:
                    print()
                print(f"🔑 Provider: {provider_name} ({provider_type}) - {'✅ Enabled' if enabled else '❌ Disabled'}")
                current_provider = provider_name
            
            # Check for problematic redirect URIs
            if config_key == 'redirect_uri':
                redirect_uri_found = True
                print(f"  📍 {config_key}: {config_value}")
                
                # Check if redirect URI has wrong host
                if 'localhost' in config_value or '127.0.0.1' in config_value or ':5000' in config_value:
                    old_redirect_uris.append((id_val, config_value))
                    print(f"    ⚠️  WARNING: Redirect URI points to localhost/port 5000")
                elif '35.200.202.18' not in config_value:
                    old_redirect_uris.append((id_val, config_value))
                    print(f"    ⚠️  WARNING: Redirect URI doesn't point to production host")
            else:
                # Mask sensitive values
                display_value = config_value
                if config_key in ['client_secret', 'client_id'] and config_value:
                    display_value = config_value[:8] + "..." if len(config_value) > 8 else "***"
                print(f"  📝 {config_key}: {display_value}")
        
        print("\n" + "="*80)
        
        # Diagnosis
        if not redirect_uri_found:
            print("❌ ISSUE: No redirect_uri found in SSO configuration")
            return False
        
        if old_redirect_uris:
            print("🔧 ISSUES FOUND:")
            for id_val, uri in old_redirect_uris:
                print(f"  - Redirect URI {id_val}: {uri}")
            print("\n💡 RECOMMENDED FIXES:")
            print("  1. Update redirect URIs to use production host: http://35.200.202.18")
            print("  2. Update OAuth provider console with new redirect URIs")
            print("  3. Restart the application")
            
            # Offer to fix automatically
            fix_choice = input("\n🛠️  Fix redirect URIs automatically? (y/N): ").strip().lower()
            if fix_choice == 'y':
                return fix_redirect_uris(cursor, conn, old_redirect_uris)
        else:
            print("✅ SSO configuration looks good!")
            print("   - Redirect URIs point to correct production host")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Error checking SSO config: {e}")
        return False

def fix_redirect_uris(cursor, conn, old_redirect_uris):
    """Fix redirect URIs to point to production host"""
    try:
        fixed_count = 0
        
        for id_val, old_uri in old_redirect_uris:
            # Build new redirect URI
            if '/auth/sso/callback/' in old_uri:
                # Extract provider from path
                provider_part = old_uri.split('/auth/sso/callback/')[-1]
                new_uri = f"http://35.200.202.18/auth/sso/callback/{provider_part}"
            else:
                # Generic fix - replace host
                new_uri = old_uri.replace('localhost', '35.200.202.18')
                new_uri = new_uri.replace('127.0.0.1', '35.200.202.18')
                new_uri = new_uri.replace(':5000', '')
                if not new_uri.startswith('http://35.200.202.18'):
                    new_uri = f"http://35.200.202.18/auth/sso/callback/oauth"
            
            # Update in database
            cursor.execute("""
                UPDATE sso_config 
                SET config_value = ?
                WHERE id = ?
            """, (new_uri, id_val))
            
            print(f"✅ Updated redirect URI {id_val}:")
            print(f"   Old: {old_uri}")
            print(f"   New: {new_uri}")
            fixed_count += 1
        
        conn.commit()
        print(f"\n🎉 Successfully fixed {fixed_count} redirect URI(s)")
        print("\n📋 NEXT STEPS:")
        print("1. Restart your Flask application:")
        print("   docker restart shift-handover-web")
        print("2. Update your OAuth provider console (Google, etc.) with the new redirect URIs")
        print("3. Test SSO login: http://35.200.202.18/login")
        
        return True
        
    except Exception as e:
        print(f"❌ Error fixing redirect URIs: {e}")
        conn.rollback()
        return False

def main():
    print("🔧 SSO Diagnosis and Fix Tool")
    print("=" * 50)
    
    # Change to app directory if needed
    if os.path.exists('app.py'):
        os.chdir('.')
    elif os.path.exists('../app.py'):
        os.chdir('..')
    
    if not os.path.exists('data/app.db'):
        print("❌ Cannot find data/app.db")
        print("   Make sure you're running this from the Flask app directory")
        sys.exit(1)
    
    if check_sso_config():
        print("\n✅ SSO diagnosis completed")
    else:
        print("\n❌ SSO diagnosis failed")
        sys.exit(1)

if __name__ == '__main__':
    main()
