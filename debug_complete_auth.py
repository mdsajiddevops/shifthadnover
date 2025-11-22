from app import app, db
from models.models import User
from flask_login import login_user, current_user, logout_user
from werkzeug.security import check_password_hash

# Initialize Flask app context
with app.app_context():
    print("=== COMPREHENSIVE AUTHENTICATION DEBUG ===")
    
    # 1. Check Flask configuration
    print(f"\n1. FLASK CONFIGURATION:")
    print(f"   SECRET_KEY set: {'Yes' if app.config.get('SECRET_KEY') else 'No'}")
    print(f"   SECRET_KEY length: {len(app.config.get('SECRET_KEY', '')) if app.config.get('SECRET_KEY') else 0}")
    print(f"   DEBUG mode: {app.debug}")
    print(f"   TESTING mode: {app.testing}")
    
    # 2. Check Flask-Login setup
    print(f"\n2. FLASK-LOGIN SETUP:")
    print(f"   Login manager exists: {hasattr(app, 'login_manager')}")
    if hasattr(app, 'login_manager'):
        print(f"   Login view: {app.login_manager.login_view}")
        print(f"   Login message: {app.login_manager.login_message}")
        print(f"   User loader registered: {app.login_manager._user_callback is not None}")
    
    # 3. Test database connection and user retrieval
    print(f"\n3. DATABASE CONNECTION:")
    try:
        user_count = User.query.count()
        print(f"   Total users in database: {user_count}")
        
        # Get superadmin user
        superadmin = User.query.filter_by(username='superadmin').first()
        if superadmin:
            print(f"   Superadmin found: ID={superadmin.id}, Username={superadmin.username}")
            print(f"   Superadmin active: {superadmin.is_active}")
            print(f"   Superadmin role: {superadmin.role}")
            
            # Test password
            password_valid = check_password_hash(superadmin.password, 'admin123')
            print(f"   Password validation: {password_valid}")
            
            # 4. Test user loader function
            print(f"\n4. USER LOADER TEST:")
            try:
                from app import load_user
                loaded_user = load_user(str(superadmin.id))
                print(f"   User loader works: {loaded_user is not None}")
                if loaded_user:
                    print(f"   Loaded user: {loaded_user.username}")
                    print(f"   User methods available: {hasattr(loaded_user, 'is_authenticated')}")
            except Exception as e:
                print(f"   User loader error: {e}")
            
            # 5. Test programmatic login
            print(f"\n5. PROGRAMMATIC LOGIN TEST:")
            with app.test_request_context('/'):
                try:
                    # Clear any existing session
                    logout_user()
                    
                    # Attempt login
                    login_result = login_user(superadmin, remember=False)
                    print(f"   Login attempt result: {login_result}")
                    print(f"   Current user authenticated: {current_user.is_authenticated}")
                    print(f"   Current user ID: {current_user.get_id() if current_user.is_authenticated else 'None'}")
                    print(f"   Current user username: {current_user.username if current_user.is_authenticated else 'None'}")
                    
                except Exception as e:
                    print(f"   Programmatic login error: {e}")
        
        else:
            print("   ❌ Superadmin user not found!")
            
    except Exception as e:
        print(f"   Database error: {e}")
    
    # 6. Check other users
    print(f"\n6. OTHER USERS:")
    try:
        users = User.query.limit(5).all()
        for user in users:
            print(f"   {user.username} (ID: {user.id}, Role: {user.role}, Active: {user.is_active})")
    except Exception as e:
        print(f"   Error listing users: {e}")
    
    # 7. Session configuration
    print(f"\n7. SESSION CONFIGURATION:")
    print(f"   Session cookie secure: {app.config.get('SESSION_COOKIE_SECURE', False)}")
    print(f"   Session cookie httponly: {app.config.get('SESSION_COOKIE_HTTPONLY', False)}")
    print(f"   Session cookie samesite: {app.config.get('SESSION_COOKIE_SAMESITE', 'None')}")
    print(f"   Permanent session lifetime: {app.config.get('PERMANENT_SESSION_LIFETIME', 'Not set')}")

print("\n=== DEBUG COMPLETE ===")