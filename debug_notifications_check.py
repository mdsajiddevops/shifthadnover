#!/usr/bin/env python3
"""
Debug notification issues for testuser2
"""

import sys
sys.path.append('/app')

from app import app, db
from models.models import User
from models.handover_enhanced import HandoverNotification

def debug_notifications():
    """Debug notification issues"""
    with app.app_context():
        print("=== DEBUGGING NOTIFICATIONS ===")
        
        # Get all test users
        test_users = User.query.filter(User.username.like('%testuser%')).all()
        print(f"\nTest users found: {len(test_users)}")
        for user in test_users:
            print(f"  {user.username} (ID: {user.id})")
        
        # Check all notifications for test users
        print("\n=== ALL NOTIFICATIONS FOR TEST USERS ===")
        for user in test_users:
            notifications = HandoverNotification.query.filter_by(recipient_id=user.id).all()
            print(f"\n{user.username} (ID: {user.id}) - {len(notifications)} notifications:")
            for notif in notifications:
                print(f"  📧 {notif.title}")
                print(f"     Type: {notif.notification_type}")
                print(f"     Read: {notif.is_read}")
                print(f"     Created: {notif.created_at}")
                print(f"     Account ID: {notif.account_id}")
                print(f"     Team ID: {notif.team_id}")
        
        # Check if there are any recent notifications at all
        print("\n=== ALL RECENT NOTIFICATIONS (Any User) ===")
        recent_notifications = HandoverNotification.query.order_by(HandoverNotification.created_at.desc()).limit(10).all()
        for notif in recent_notifications:
            recipient = User.query.get(notif.recipient_id)
            print(f"  To: {recipient.username if recipient else 'Unknown'} (ID: {notif.recipient_id})")
            print(f"  Title: {notif.title}")
            print(f"  Created: {notif.created_at}")
            print(f"  ---")
        
        print("\n=== CHECKING INCIDENT RESPONSE LOGS ASSIGNEE ISSUE ===")
        
        # Import the models we need for incident response logs
        try:
            from models.handover_enhanced import HandoverIncidentResponseLog
            
            # Get recent incident response logs
            logs = HandoverIncidentResponseLog.query.order_by(HandoverIncidentResponseLog.created_at.desc()).limit(10).all()
            print(f"\nFound {len(logs)} recent incident response logs:")
            
            for log in logs:
                print(f"  Incident: {log.incident_title}")
                print(f"  Assigned to: {log.assigned_to}")
                print(f"  Response: {log.response_type}")
                print(f"  Created: {log.created_at}")
                print(f"  ---")
                
        except Exception as e:
            print(f"Error checking incident response logs: {e}")

if __name__ == "__main__":
    debug_notifications()