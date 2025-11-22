import sys
sys.path.append('/app')
from datetime import datetime
from app import app, db
from models.models import User
from werkzeug.security import generate_password_hash

with app.app_context():
    # Create a simple test user
    test_username = 'sso_test_' + datetime.now().strftime('%H%M%S')
    
    # Remove existing test user if any
    existing = User.query.filter_by(username=test_username).first()
    if existing:
        db.session.delete(existing)
        db.session.commit()
    
    # Create new test user with minimal required fields
    test_user = User(
        username=test_username,
        email=test_username + '@example.com',
        password=generate_password_hash('testpass123'),
        role='user'
    )
    
    # Set the fields that trigger onboarding
    test_user.account_id = None
    test_user.team_id = None
    test_user.onboarding_completed = False
    test_user.first_login = True
    
    db.session.add(test_user)
    db.session.commit()
    
    print(' Test user created successfully!')
    print('Username:', test_user.username)
    print('Password: testpass123')
    print('Needs Onboarding:', test_user.needs_onboarding)
    print('Expected: Should redirect to /onboarding on login')
