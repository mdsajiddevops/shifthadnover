#!/usr/bin/env python3
from werkzeug.security import generate_password_hash

# Generate password hash for 'admin123'
password = 'admin123'
hash_value = generate_password_hash(password)
print(f"Password hash for 'admin123': {hash_value}")

# Create SQL update statement
sql = f"UPDATE user SET password = '{hash_value}' WHERE username = 'superadmin';"
print(f"\nSQL Update Statement:")
print(sql)