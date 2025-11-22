#!/usr/bin/env python3
"""
Create a test user for onboarding workflow testing
This user will have needs_onboarding=True to trigger the onboarding flow
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app, db
from models.models import User
from werkzeug.security import generate_password_hash

def create_test_user():
    with app.app_context():
        try:
            # Check if test user already exists
            existing_user = User.query.filter_by(username='testuser').first()
            if existing_user:
                print("Test user 'testuser' already exists. Deleting and recreating...")
                db.session.delete(existing_user)
                db.session.commit()
            
            # Create the test user with proper password hash
            password_hash = generate_password_hash('test123')
            
            test_user = User(
                username='testuser',
                email='testuser@epam.com',
                password=password_hash,
                first_name='Test',
                last_name='User',
                role='user',
                is_active=True,
                needs_onboarding=True,  # This will trigger the onboarding workflow
                default_account_id=None,  # Will be set during onboarding
                default_team_id=None     # Will be set during onboarding
            )
            
            db.session.add(test_user)
            db.session.commit()
            
            print("✅ Test user created successfully!")
            print(f"Username: testuser")
            print(f"Password: test123")
            print(f"Email: testuser@epam.com")
            print(f"needs_onboarding: True")
            print("\nThis user can now be used to test the onboarding workflow.")
            print("When they log in, they should be redirected to the onboarding process.")
            
        except Exception as e:
            print(f"❌ Error creating test user: {e}")
            db.session.rollback()
            return False
        
        return True

if __name__ == '__main__':
    success = create_test_user()
    if success:
        print("\n🎉 Test user ready for onboarding workflow testing!")
    else:
        print("\n❌ Failed to create test user.")
        sys.exit(1)