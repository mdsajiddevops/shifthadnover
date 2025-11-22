#!/usr/bin/env python3
"""
Test handover notification creation from testuser1 to testuser2 and testuser3
"""

import sys
sys.path.append('/app')

from app import app, db
from models.models import User, Shift, Incident, ShiftKeyPoint, TeamMember
from models.handover_enhanced import HandoverRequest, HandoverNotification
from datetime import datetime, date
from services.notification_service_fix import notification_fix

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
        print(f"  testuser1: ID {testuser1.id}")
        print(f"  testuser2: ID {testuser2.id}")
        print(f"  testuser3: ID {testuser3.id}")
        
        # Create a new HandoverRequest
        handover_request = HandoverRequest(
            shift_date=date.today(),
            current_shift_type='Morning',
            next_shift_type='Evening',
            created_by_id=testuser1.id,
            status='pending',
            general_notes='Test handover from testuser1',
            shift_summary='Testing notification system'
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

if __name__ == "__main__":
    create_test_handover()