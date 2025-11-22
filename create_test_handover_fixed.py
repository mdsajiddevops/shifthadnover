#!/usr/bin/env python3
"""
Test handover notification creation from testuser1 to testuser2 and testuser3 (Fixed)
"""

import sys
sys.path.append('/app')

from app import app, db
from models.models import User
from models.handover_enhanced import HandoverRequest, HandoverNotification
from datetime import datetime, date

def create_test_handover():
    """Create test handover and notifications"""
    with app.app_context():
        print("=== CREATING TEST HANDOVER FROM testuser1 TO testuser2 & testuser3 ===")
        
        # Get the test users
        testuser1 = User.query.filter_by(username='testuser1').first()
        testuser2 = User.query.filter_by(username='testuser2').first()
        testuser3 = User.query.filter_by(username='testuser3').first()
        
        if not all([testuser1, testuser2, testuser3]):
            print("❌ Test users not found!")
            return
        
        print(f"✅ Found test users:")
        print(f"  testuser1: ID {testuser1.id}, Account: {testuser1.account_id}, Team: {testuser1.team_id}")
        print(f"  testuser2: ID {testuser2.id}, Account: {testuser2.account_id}, Team: {testuser2.team_id}")
        print(f"  testuser3: ID {testuser3.id}, Account: {testuser3.account_id}, Team: {testuser3.team_id}")
        
        # Create a new HandoverRequest with proper account_id and team_id
        handover_request = HandoverRequest(
            shift_date=date.today(),
            current_shift_type='Morning',
            next_shift_type='Evening',
            created_by_id=testuser1.id,
            status='pending',
            general_notes='Test handover from testuser1',
            shift_summary='Testing notification system',
            account_id=testuser1.account_id or 1,  # Default to TechCorp Solutions
            team_id=testuser1.team_id or 2  # Default to Operations Team
        )
        
        db.session.add(handover_request)
        db.session.commit()
        
        print(f"✅ Created HandoverRequest ID: {handover_request.id}")
        
        # Create test notifications for testuser2 and testuser3
        notifications_to_create = [
            {
                'recipient_id': testuser2.id,
                'handover_request_id': handover_request.id,
                'notification_type': 'handover_assigned',
                'title': f'New Handover Assignment from {testuser1.username}',
                'message': f'You have been assigned a handover from {testuser1.username} for {date.today()}'
            },
            {
                'recipient_id': testuser3.id,
                'handover_request_id': handover_request.id,
                'notification_type': 'handover_assigned',
                'title': f'New Handover Assignment from {testuser1.username}', 
                'message': f'You have been assigned a handover from {testuser1.username} for {date.today()}'
            }
        ]
        
        for notif_data in notifications_to_create:
            notification = HandoverNotification(
                recipient_id=notif_data['recipient_id'],
                handover_request_id=notif_data['handover_request_id'],
                notification_type=notif_data['notification_type'],
                title=notif_data['title'],
                message=notif_data['message'],
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
        
        print("\n✅ Test handover and notifications created successfully!")
        print("\n🔍 Now try logging in as testuser2 or testuser3 to see the notifications")
        print("   Username: testuser2, Password: password123")
        print("   Username: testuser3, Password: password123")
        print(f"\n🌐 Access the application at: https://shiftops.lab.epam.com/")

if __name__ == "__main__":
    create_test_handover()