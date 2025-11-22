#!/usr/bin/env python3
import sys
sys.path.append('/app')
import os

# Read the current auth.py file
with open('/app/routes/auth.py', 'r') as f:
    content = f.read()

# Add debug logging to the login route
debug_lines = '''
        print(f"DEBUG: Login attempt - username: '{username}', password: '{password}'")
        print(f"DEBUG: Form data: {dict(request.form)}")
        print(f"DEBUG: User query result: {user}")
        if user:
            print(f"DEBUG: User role: '{user.role}', is_active: {user.is_active}, status: '{user.status}'")
            print(f"DEBUG: Role check (super_admin): {user.role == 'super_admin'}")
            if user.role == 'super_admin':
                password_valid = check_password_hash(user.password, password)
                print(f"DEBUG: Password check result: {password_valid}")
'''

# Find the line where we start checking the user and add debug logging
if "user = User.query.filter_by(username=username).first()" in content:
    # Add debug logging after getting the user
    content = content.replace(
        "user = User.query.filter_by(username=username).first()",
        f"user = User.query.filter_by(username=username).first(){debug_lines}"
    )
    
    # Write the modified content
    with open('/app/routes/auth_debug.py', 'w') as f:
        f.write(content)
    
    print("Debug version created successfully")
else:
    print("Could not find the target line to add debug logging")