#!/usr/bin/env python3
"""
Create or update test users and check notification creation
"""

import sys
sys.path.append('/app')

from app import app, db
from models.models import User
from models.handover_enhanced import HandoverNotification
from werkzeug.security import generate_password_hash

def create_test_users():
    """Create or update testuser1, testuser2, testuser3"""
    with app.app_context():
        print("=== CREATING/UPDATING TEST USERS ===")
        
        # Test users to create/update
        test_users_data = [
            {'username': 'testuser1', 'email': 'testuser1@example.com'},
            {'username': 'testuser2', 'email': 'testuser2@example.com'},
            {'username': 'testuser3', 'email': 'testuser3@example.com'}
        ]
        
        for user_data in test_users_data:
            # Check if user exists
            existing_user = User.query.filter_by(username=user_data['username']).first()
            
            if existing_user:
                print(f"  ✅ User {user_data['username']} already exists (ID: {existing_user.id})")
                # Update team_id if needed
                if existing_user.team_id != 2:
                    existing_user.team_id = 2
                    existing_user.account_id = 1  # TechCorp Solutions
                    db.session.commit()
                    print(f"    🔧 Updated team_id to 2 for {user_data['username']}")
            else:
                # Create new user
                new_user = User(
                    username=user_data['username'],
                    email=user_data['email'],
                    password=generate_password_hash('password123'),
                    role='user',
                    team_id=2,  # Operations Team
                    account_id=1,  # TechCorp Solutions
                    status='active',
                    is_active=True
                )
                db.session.add(new_user)
                db.session.commit()
                print(f"  ✨ Created new user {user_data['username']} (ID: {new_user.id})")
        
        print("\n=== CURRENT TEST USERS ===")
        test_users = User.query.filter(User.username.in_(['testuser1', 'testuser2', 'testuser3'])).all()
        for user in test_users:
            print(f"  ID: {user.id}, Username: {user.username}, Email: {user.email}, Team: {user.team_id}")
        
        print("\n=== CHECKING RECENT NOTIFICATIONS ===")
        recent_notifications = HandoverNotification.query.order_by(HandoverNotification.created_at.desc()).limit(5).all()
        print(f"Found {len(recent_notifications)} recent notifications:")
        
        for notif in recent_notifications:
            recipient = User.query.get(notif.recipient_id)
            print(f"  To: {recipient.username if recipient else 'Unknown'} (ID: {notif.recipient_id})")
            print(f"  Type: {notif.notification_type}")
            print(f"  Title: {notif.title}")
            print(f"  Handover Request ID: {notif.handover_request_id}")
            print(f"  Read: {notif.is_read}")
            print(f"  Created: {notif.created_at}")
            print(f"  ---")

if __name__ == "__main__":
    create_test_users()