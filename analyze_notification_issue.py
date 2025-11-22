#!/usr/bin/env python3
"""
Analyze Notification Assignment Issue
Check why notifications are going to wrong users
"""

import sys
sys.path.append('/app')

from app import app, db
from models.models import User
from models.handover_enhanced import HandoverRequest, HandoverNotification, HandoverIncidentResponseLog
from sqlalchemy import desc

def analyze_notification_issue():
    """Analyze why notifications are going to wrong users"""
    
    print("🔍 NOTIFICATION ASSIGNMENT ANALYSIS")
    print("=" * 60)
    
    with app.app_context():
        # Get the latest handover request
        latest_request = HandoverRequest.query.filter_by(team_id=2).order_by(desc(HandoverRequest.created_at)).first()
        
        if not latest_request:
            print("❌ No handover requests found")
            return
        
        creator = User.query.get(latest_request.created_by_id)
        print(f"📋 LATEST HANDOVER REQUEST:")
        print(f"   ID: {latest_request.id}")
        print(f"   Created by: {creator.username if creator else 'Unknown'} (ID: {latest_request.created_by_id})")
        print(f"   Created at: {latest_request.created_at}")
        print(f"   Status: {latest_request.status}")
        print()
        
        # Get notifications for this request
        notifications = HandoverNotification.query.filter_by(
            handover_request_id=latest_request.id
        ).all()
        
        print(f"📧 NOTIFICATIONS FOR THIS REQUEST:")
        print(f"   Total notifications: {len(notifications)}")
        
        for notif in notifications:
            recipient = User.query.get(notif.recipient_id)
            print(f"   - Notification ID: {notif.id}")
            print(f"     To: {recipient.username if recipient else 'Unknown'} (ID: {notif.recipient_id})")
            print(f"     Title: {notif.title}")
            print(f"     Type: {notif.notification_type}")
            print()
        
        # Check if techopsuser2 got any notifications
        techopsuser2 = User.query.filter_by(username='techopsuser2').first()
        if techopsuser2:
            user2_notifications = HandoverNotification.query.filter_by(
                recipient_id=techopsuser2.id
            ).all()
            
            print(f"🎯 TECHOPSUSER2 NOTIFICATIONS:")
            print(f"   Total for techopsuser2: {len(user2_notifications)}")
            
            if user2_notifications:
                for notif in user2_notifications:
                    print(f"   - {notif.title} (Created: {notif.created_at})")
            else:
                print("   ❌ NO notifications found for techopsuser2")
        
        # Analyze the problem
        print(f"\n🚨 PROBLEM ANALYSIS:")
        print("-" * 40)
        
        expected_recipients = ['techopsuser2']
        actual_recipients = [User.query.get(notif.recipient_id).username for notif in notifications if User.query.get(notif.recipient_id)]
        
        print(f"Expected recipients: {expected_recipients}")
        print(f"Actual recipients: {actual_recipients}")
        
        if set(expected_recipients) != set(actual_recipients):
            print("❌ MISMATCH: Notifications going to wrong users!")
            print("\n🔧 LIKELY CAUSES:")
            print("1. Incident assignment form may be using wrong user IDs")
            print("2. Dropdown selection may be mapping to wrong users")
            print("3. Form data processing may be incorrect")
            
            # Check which users these IDs actually belong to
            print(f"\n👥 WHO ARE THE ACTUAL RECIPIENTS?")
            for notif in notifications:
                recipient = User.query.get(notif.recipient_id)
                if recipient:
                    print(f"   User ID {notif.recipient_id}: {recipient.username} ({recipient.email})")
                    print(f"     Account: {recipient.account_id}, Team: {recipient.team_id}")
        
        # Check response logs
        print(f"\n📊 RESPONSE LOGS:")
        response_logs = HandoverIncidentResponseLog.query.filter_by(
            team_id=2
        ).order_by(desc(HandoverIncidentResponseLog.created_at)).limit(3).all()
        
        for log in response_logs:
            print(f"   - {log.incident_title}")
            print(f"     Assigned by: {log.assigned_by_name}")
            print(f"     Accepted by: {log.accepted_by_name}")
            print(f"     Created: {log.created_at}")
        
        print(f"\n💡 SOLUTION:")
        print("The issue is in the incident assignment form.")
        print("When creating handovers, the form is selecting wrong users from dropdowns.")
        print("Need to check the user selection dropdown in the handover creation form.")

if __name__ == "__main__":
    analyze_notification_issue()