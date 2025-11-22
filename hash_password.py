from werkzeug.security import generate_password_hash
password_hash = generate_password_hash('admin123')
print(f'Password hash: {password_hash}')
