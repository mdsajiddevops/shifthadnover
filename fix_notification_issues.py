#!/usr/bin/env python3
"""
Fix notification display and incident response log assignee issues
"""

import sys
sys.path.append('/app')

from app import app, db
from models.models import User
from models.handover_enhanced import HandoverNotification, HandoverIncidentResponseLog

def fix_notification_issues():
    """Fix notification and assignee display issues"""
    with app.app_context():
        print("=== FIXING NOTIFICATION AND ASSIGNEE ISSUES ===")
        
        # Issue 1: Check if notifications are correctly associated
        print("\n1. CHECKING NOTIFICATION RECIPIENTS")
        
        testuser2 = User.query.filter_by(username='testuser2').first()
        testuser3 = User.query.filter_by(username='testuser3').first()
        
        if testuser2:
            notifications_2 = HandoverNotification.query.filter_by(recipient_id=testuser2.id).all()
            print(f"testuser2 (ID: {testuser2.id}) has {len(notifications_2)} notifications")
            
        if testuser3:
            notifications_3 = HandoverNotification.query.filter_by(recipient_id=testuser3.id).all()
            print(f"testuser3 (ID: {testuser3.id}) has {len(notifications_3)} notifications")
        
        # Issue 2: Check the incident response logs structure
        print("\n2. CHECKING INCIDENT RESPONSE LOG STRUCTURE")
        
        try:
            # Get recent logs and show their actual structure
            logs = HandoverIncidentResponseLog.query.order_by(HandoverIncidentResponseLog.created_at.desc()).limit(5).all()
            print(f"Found {len(logs)} recent incident response logs")
            
            if logs:
                log = logs[0]
                print(f"\nFirst log attributes:")
                for attr in dir(log):
                    if not attr.startswith('_') and not callable(getattr(log, attr)):
                        try:
                            value = getattr(log, attr)
                            print(f"  {attr}: {value}")
                        except:
                            print(f"  {attr}: <error reading>")
                            
        except Exception as e:
            print(f"Error checking incident response logs: {e}")
        
        # Issue 3: Check why dashboard is not finding notifications for testuser2
        print("\n3. CHECKING DASHBOARD NOTIFICATION QUERY")
        
        # Simulate the dashboard query for testuser2
        if testuser2:
            print(f"Simulating dashboard query for testuser2 (ID: {testuser2.id})")
            dashboard_notifications = HandoverNotification.query.filter_by(
                recipient_id=testuser2.id,
                is_read=False
            ).all()
            print(f"Dashboard would find {len(dashboard_notifications)} unread notifications")
            
            for notif in dashboard_notifications:
                print(f"  - {notif.title} (Created: {notif.created_at})")
        
        # Issue 4: Check if there's a mismatch in user sessions
        print("\n4. CHECKING USER SESSION ISSUES")
        print("The logs show dashboard queries for techopsuser2 (ID: 41) instead of testuser2 (ID: 47)")
        print("This suggests you might be logging in as techopsuser2 instead of testuser2")
        print("\nTo fix this:")
        print("1. Make sure you're logging in with username 'testuser2' (not 'techopsuser2')")
        print("2. Password should be 'password123'")
        print("3. Clear browser cache/cookies if needed")
        
        print("\n=== RECOMMENDATIONS ===")
        print("1. Login as 'testuser2' with password 'password123'")
        print("2. The notifications exist and should appear in the dashboard")
        print("3. For incident response logs, the assignee field might be named differently")
        
        # Let's check what field contains the assignee information
        print("\n5. ANALYZING INCIDENT RESPONSE LOG ASSIGNEE FIELD")
        try:
            logs = HandoverIncidentResponseLog.query.limit(1).all()
            if logs:
                log = logs[0]
                assignee_fields = [attr for attr in dir(log) if 'assign' in attr.lower() or 'user' in attr.lower() or 'name' in attr.lower()]
                print(f"Potential assignee fields: {assignee_fields}")
                
                for field in assignee_fields:
                    if not field.startswith('_') and not callable(getattr(log, field)):
                        try:
                            value = getattr(log, field)
                            print(f"  {field}: {value}")
                        except:
                            pass
        except Exception as e:
            print(f"Error analyzing assignee fields: {e}")

if __name__ == "__main__":
    fix_notification_issues()