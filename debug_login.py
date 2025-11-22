from app import app, db
from models.models import User
from flask_login import login_user, current_user
from werkzeug.security import check_password_hash

# Initialize Flask app context
with app.app_context():
    print("=== FLASK LOGIN DEBUG ===")
    
    # Check Flask configuration
    print(f"SECRET_KEY set: {'Yes' if app.config.get('SECRET_KEY') else 'No'}")
    print(f"SECRET_KEY length: {len(app.config.get('SECRET_KEY', ''))}")
    print(f"LOGIN_VIEW: {app.config.get('LOGIN_VIEW')}")
    
    # Check if user can be found and authenticated
    superadmin = User.query.filter_by(username='superadmin').first()
    if superadmin:
        print(f"\n=== USER CHECK ===")
        print(f"User found: {superadmin.username}")
        print(f"User active: {superadmin.is_active}")
        print(f"User role: {superadmin.role}")
        
        # Test password
        password_valid = check_password_hash(superadmin.password, 'admin123')
        print(f"Password valid: {password_valid}")
        
        # Test if user can be logged in programmatically
        with app.test_request_context():
            from flask_login import login_user, current_user
            login_result = login_user(superadmin)
            print(f"Login successful: {login_result}")
            print(f"Current user authenticated: {current_user.is_authenticated if current_user else 'No current user'}")
            print(f"Current user: {current_user.username if current_user and current_user.is_authenticated else 'Anonymous'}")
    
    # Check Flask-Login configuration
    print(f"\n=== FLASK-LOGIN CONFIG ===")
    print(f"Login manager: {hasattr(app, 'login_manager')}")
    if hasattr(app, 'login_manager'):
        print(f"User loader: {app.login_manager._user_callback is not None}")
        print(f"Login view: {app.login_manager.login_view}")
        print(f"Login message: {app.login_manager.login_message}")