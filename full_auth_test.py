#!/usr/bin/env python3
import sys
sys.path.append('/app')

from models.models import User
from werkzeug.security import check_password_hash
from app import app

with app.app_context():
    # Test the exact login flow
    username = 'superadmin'
    password = 'admin123'
    
    print(f"Testing login for username: '{username}' with password: '{password}'")
    
    user = User.query.filter_by(username=username).first()
    
    if user:
        print(f"✅ User found")
        print(f"   Username: {user.username}")
        print(f"   Role: '{user.role}'")
        print(f"   Is Active: {user.is_active}")
        print(f"   Status: '{user.status}'")
        
        # Test each condition in the auth logic
        print(f"\n🔍 Testing authentication conditions:")
        
        # Check if user exists and role is super_admin
        role_check = user and user.role == 'super_admin'
        print(f"   user and user.role == 'super_admin': {role_check}")
        
        if role_check:
            # Check password
            password_valid = check_password_hash(user.password, password)
            print(f"   check_password_hash(user.password, password): {password_valid}")
            
            if password_valid:
                print(f"✅ Authentication should SUCCEED")
            else:
                print(f"❌ Authentication should FAIL - password invalid")
        else:
            print(f"❌ Authentication should FAIL - role check failed")
            
    else:
        print(f"❌ User not found")

    print(f"\n🔍 All users in database:")
    all_users = User.query.all()
    for u in all_users:
        print(f"   ID: {u.id}, Username: '{u.username}', Role: '{u.role}', Active: {u.is_active}")