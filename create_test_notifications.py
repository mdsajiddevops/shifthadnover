#!/usr/bin/env python3
"""
Create simple test notifications for testuser2 and testuser3
"""

import sys
sys.path.append('/app')

from app import app, db
from models.models import User
from models.handover_enhanced import HandoverNotification
from datetime import datetime

def create_test_notifications():
    """Create test notifications directly"""
    with app.app_context():
        print("=== CREATING TEST NOTIFICATIONS FOR testuser2 & testuser3 ===")
        
        # Get the test users
        testuser1 = User.query.filter_by(username='testuser1').first()
        testuser2 = User.query.filter_by(username='testuser2').first()
        testuser3 = User.query.filter_by(username='testuser3').first()
        
        if not all([testuser1, testuser2, testuser3]):
            print("❌ Test users not found!")
            return
        
        print(f"✅ Found test users:")
        print(f"  testuser1: ID {testuser1.id}")
        print(f"  testuser2: ID {testuser2.id}")
        print(f"  testuser3: ID {testuser3.id}")
        
        # Create test notifications for testuser2 and testuser3
        notifications_to_create = [
            {
                'recipient_id': testuser2.id,
                'notification_type': 'handover_assigned',
                'title': f'New Handover Assignment from {testuser1.username}',
                'message': f'You have been assigned a handover from {testuser1.username} for today.',
                'account_id': testuser2.account_id or 1,
                'team_id': testuser2.team_id or 2
            },
            {
                'recipient_id': testuser3.id,
                'notification_type': 'handover_assigned',
                'title': f'New Handover Assignment from {testuser1.username}', 
                'message': f'You have been assigned a handover from {testuser1.username} for today.',
                'account_id': testuser3.account_id or 1,
                'team_id': testuser3.team_id or 2
            }
        ]
        
        for notif_data in notifications_to_create:
            notification = HandoverNotification(
                recipient_id=notif_data['recipient_id'],
                handover_request_id=None,  # No specific handover request
                notification_type=notif_data['notification_type'],
                title=notif_data['title'],
                message=notif_data['message'],
                account_id=notif_data['account_id'],
                team_id=notif_data['team_id'],
                is_read=False,
                created_at=datetime.utcnow()
            )
            db.session.add(notification)
        
        db.session.commit()
        print(f"✅ Created {len(notifications_to_create)} notifications")
        
        # Verify the notifications were created
        print("\n=== VERIFYING NOTIFICATIONS ===")
        
        for user in [testuser2, testuser3]:
            notifications = HandoverNotification.query.filter_by(recipient_id=user.id).all()
            print(f"\n{user.username} (ID: {user.id}) notifications:")
            for notif in notifications:
                print(f"  📧 {notif.title}")
                print(f"     Type: {notif.notification_type}")
                print(f"     Read: {notif.is_read}")
                print(f"     Created: {notif.created_at}")
        
        print("\n✅ Test notifications created successfully!")
        print("\n🔍 Now try logging in as testuser2 or testuser3 to see the notifications")
        print("   Username: testuser2, Password: password123")
        print("   Username: testuser3, Password: password123")
        print(f"\n🌐 Access the application at: https://shiftops.lab.epam.com/")
        print("\n   Or through the dashboard to see notification count in the header")

if __name__ == "__main__":
    create_test_notifications()