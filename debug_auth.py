from app import app, db
from models.models import User
from werkzeug.security import check_password_hash, generate_password_hash

# Initialize Flask app context
with app.app_context():
    # Check all users and their password hashes
    users = User.query.limit(5).all()
    print("=== USER AUTHENTICATION DEBUG ===")
    
    for user in users:
        print(f"\nUser: {user.username}")
        print(f"Email: {user.email}")
        print(f"Role: {user.role}")
        print(f"Active: {user.is_active}")
        print(f"Password hash start: {user.password[:30]}...")
        
        # Test if this is a Werkzeug hash
        if user.password.startswith('pbkdf2:sha256:') or user.password.startswith('scrypt:'):
            print("✅ Werkzeug compatible hash detected")
        else:
            print("⚠️ Non-Werkzeug hash detected - may need conversion")
    
    # Try to find superadmin and test authentication
    superadmin = User.query.filter_by(username='superadmin').first()
    if superadmin:
        print(f"\n=== SUPERADMIN TEST ===")
        print(f"Username: {superadmin.username}")
        print(f"Email: {superadmin.email}")
        print(f"Hash type: {superadmin.password[:20]}...")
        
        # Common passwords to test
        test_passwords = ['admin', 'admin123', 'password', 'superadmin', '123456']
        for pwd in test_passwords:
            if check_password_hash(superadmin.password, pwd):
                print(f"✅ Password '{pwd}' works!")
                break
        else:
            print("❌ None of the test passwords work")
            print("💡 Password may need to be reset")