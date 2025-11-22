from werkzeug.security import check_password_hash
import sys
import os
sys.path.append('/app')
from app import app
from models.models import User

def test_password():
    with app.app_context():
        user = User.query.filter_by(username='testuser').first()
        if user:
            print(f'User found: {user.username}')
            print(f'Email: {user.email}')
            print(f'Role: {user.role}')
            print(f'Is Active: {user.is_active}')
            print(f'Status: {user.status}')
            print(f'First Login: {user.first_login}')
            print(f'Onboarding Completed: {user.onboarding_completed}')
            print(f'Account ID: {user.account_id}')
            print(f'Team ID: {user.team_id}')
            print(f'Needs Onboarding: {user.needs_onboarding}')
            print(f'Password Hash (first 50 chars): {user.password[:50]}...')
            
            # Test password verification
            password_valid = check_password_hash(user.password, 'test123')
            print(f'Password " test123\ valid: {password_valid}')
 
 if not password_valid:
 print(' PASSWORD VERIFICATION FAILED')
 else:
 print(' PASSWORD VERIFICATION SUCCESSFUL')
 else:
 print(' User not found')

if __name__ == '__main__':
 test_password()
