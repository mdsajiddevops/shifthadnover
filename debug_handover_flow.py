#!/usr/bin/env python3
"""
Debug Handover Submission Flow
Check what happens when handovers are submitted and why notifications aren't created
"""

import sys
sys.path.append('/app')

from app import app, db
from models.models import User
from models.handover_enhanced import (
    HandoverRequest, HandoverNotification, HandoverIncidentResponseLog
)
from sqlalchemy import text, desc

def debug_handover_flow():
    """Debug the handover submission and notification creation flow"""
    
    print("🔍 DEBUGGING HANDOVER SUBMISSION FLOW")
    print("=" * 80)
    
    with app.app_context():
        # Check users first
        techopsuser1 = User.query.filter_by(username='techopsuser1').first()
        techopsuser2 = User.query.filter_by(username='techopsuser2').first()
        
        print("👥 USER STATUS:")
        print(f"   techopsuser1: {'✅ Found' if techopsuser1 else '❌ Not Found'} (ID: {techopsuser1.id if techopsuser1 else 'N/A'})")
        print(f"   techopsuser2: {'✅ Found' if techopsuser2 else '❌ Not Found'} (ID: {techopsuser2.id if techopsuser2 else 'N/A'})")
        print()
        
        # Check recent handover requests
        print("📋 RECENT HANDOVER REQUESTS:")
        print("-" * 50)
        
        recent_requests = HandoverRequest.query.filter_by(
            team_id=2  # Operations Team
        ).order_by(desc(HandoverRequest.created_at)).limit(5).all()
        
        if recent_requests:
            for req in recent_requests:
                creator = User.query.get(req.created_by_id)
                print(f"Request ID: {req.id}")
                print(f"   Created by: {creator.username if creator else f'ID:{req.created_by_id}'}")
                print(f"   Created at: {req.created_at}")
                print(f"   Status: {req.status}")
                print(f"   Team: {req.team_id}")
                print(f"   Account: {req.account_id}")
                print()
        else:
            print("❌ No recent handover requests found")
            print("⚠️ This suggests handover submission may have failed")
        
        # Check handover notifications
        print("📧 HANDOVER NOTIFICATIONS:")
        print("-" * 50)
        
        all_notifications = HandoverNotification.query.order_by(
            desc(HandoverNotification.created_at)
        ).limit(10).all()
        
        if all_notifications:
            for notif in all_notifications:
                recipient = User.query.get(notif.recipient_id)
                print(f"Notification ID: {notif.id}")
                print(f"   Recipient: {recipient.username if recipient else f'ID:{notif.recipient_id}'}")
                print(f"   Title: {notif.title}")
                print(f"   Type: {notif.notification_type}")
                print(f"   Created: {notif.created_at}")
                print(f"   Read: {'Yes' if notif.is_read else 'No'}")
                if notif.handover_request_id:
                    print(f"   Request ID: {notif.handover_request_id}")
                print()
        else:
            print("❌ No handover notifications found")
            print("⚠️ This confirms notifications are not being created")
        
        # Check handover incident response logs
        print("📊 HANDOVER INCIDENT RESPONSE LOGS:")
        print("-" * 50)
        
        response_logs = HandoverIncidentResponseLog.query.filter_by(
            team_id=2
        ).order_by(desc(HandoverIncidentResponseLog.created_at)).limit(10).all()
        
        if response_logs:
            for log in response_logs:
                print(f"Log ID: {log.id}")
                print(f"   Incident: {log.incident_title}")
                print(f"   Assigned by: {log.assigned_by_name}")
                print(f"   Accepted by: {log.accepted_by_name}")
                print(f"   Status: {log.status}")
                print(f"   Created: {log.created_at}")
                print()
        else:
            print("❌ No recent response logs found")
        
        # Check if notification service is working
        print("🔧 NOTIFICATION SERVICE STATUS:")
        print("-" * 50)
        
        # Check if the notification service file exists and is correct
        try:
            with open('/app/services/notification_service_fix.py', 'r') as f:
                content = f.read()
                if 'getlist()' in content:
                    print("❌ FOUND ISSUE: notification_service_fix.py still contains .getlist() calls")
                    print("⚠️ This will cause notification creation to fail")
                else:
                    print("✅ notification_service_fix.py looks clean (no .getlist() calls)")
        except FileNotFoundError:
            print("❌ notification_service_fix.py not found")
        
        # Check for any error logs or issues
        print("\n🚨 TROUBLESHOOTING RECOMMENDATIONS:")
        print("-" * 50)
        
        if not recent_requests:
            print("1. ❌ HANDOVER NOT SUBMITTED: Check if handover form submission is working")
            print("   • Login as techopsuser1")
            print("   • Try to submit a simple handover")
            print("   • Check for JavaScript errors in browser console")
        
        if recent_requests and not all_notifications:
            print("2. ❌ NOTIFICATION CREATION FAILED: Handover submitted but no notifications created")
            print("   • Check notification_service_fix.py for errors")
            print("   • Check Flask logs for notification creation errors")
            print("   • Verify form data processing in handover route")
        
        if not response_logs:
            print("3. ❌ RESPONSE LOGS NOT CREATED: Incident assignments not being logged")
            print("   • Check if incidents are being assigned correctly")
            print("   • Verify HandoverIncidentResponseLog creation in code")
        
        print("\n🛠️ IMMEDIATE ACTIONS:")
        print("1. Check browser console for JavaScript errors during handover submission")
        print("2. Check Flask application logs for notification creation errors")
        print("3. Verify the handover form is submitting data correctly")
        print("4. Test with a simple incident assignment to isolate the issue")

if __name__ == "__main__":
    debug_handover_flow()