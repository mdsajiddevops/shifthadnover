from werkzeug.security import check_password_hash, generate_password_hash

# Test the fresh hash directly
fresh_hash = 'scrypt:32768:8:1\\'

print('Testing fresh hash directly:')
print('Hash:', fresh_hash[:50] + '...')
print('Password test123 valid:', check_password_hash(fresh_hash, 'test123'))

# Generate and test a new hash immediately  
new_hash = generate_password_hash('test123')
print()
print('Testing newly generated hash:')
print('New hash:', new_hash[:50] + '...')
print('Password test123 valid:', check_password_hash(new_hash, 'test123'))
