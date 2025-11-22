#!/usr/bin/env python3
"""
Cleanup script to remove all handover reports and notification data 
for Account "TechCorp Solutions" (ID: 1) and Team "Operations Team" (ID: 2)
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import the Flask app and database
from app import app, db
from models.models import User
from models.handover_enhanced import (
    HandoverRequest, HandoverNotification, IncidentAssignment, 
    HandoverIncidentResponseLog
)
from models.models import Shift
from sqlalchemy import text

def cleanup_techcorp_data():
    """Clean up all handover data for TechCorp Solutions (Account ID: 1) and Operations Team (Team ID: 2)"""
    
    account_id = 1  # TechCorp Solutions
    team_id = 2     # Operations Team
    
    print(f"🧹 Starting cleanup for Account ID {account_id} (TechCorp Solutions) and Team ID {team_id} (Operations Team)")
    
    try:
        # 1. Find and delete HandoverNotifications for users in this team
        notifications_deleted = 0
        
        # Get all users who are team members of Operations Team
        team_member_user_ids = db.session.execute(
            text("SELECT DISTINCT user_id FROM team_member WHERE team_id = :team_id AND user_id IS NOT NULL"),
            {"team_id": team_id}
        ).fetchall()
        
        user_ids = [row[0] for row in team_member_user_ids if row[0]]
        print(f"📋 Found {len(user_ids)} users in Operations Team: {user_ids}")
        
        if user_ids:
            # Delete notifications for these users
            notifications = HandoverNotification.query.filter(
                HandoverNotification.recipient_id.in_(user_ids)
            ).all()
            
            for notification in notifications:
                print(f"  🗑️ Deleting notification: {notification.title} for user {notification.recipient_id}")
                db.session.delete(notification)
                notifications_deleted += 1
        
        # 2. Delete IncidentAssignments for this account/team
        assignments = IncidentAssignment.query.filter_by(
            account_id=account_id, 
            team_id=team_id
        ).all()
        
        assignments_deleted = len(assignments)
        for assignment in assignments:
            print(f"  🗑️ Deleting incident assignment: {assignment.incident_title}")
            db.session.delete(assignment)
        
        # 3. Delete HandoverIncidentResponseLog entries for this account/team
        logs = HandoverIncidentResponseLog.query.filter_by(
            account_id=account_id,
            team_id=team_id
        ).all()
        
        logs_deleted = len(logs)
        for log in logs:
            print(f"  🗑️ Deleting response log: {log.incident_title}")
            db.session.delete(log)
        
        # 4. Delete Shifts for this account/team
        shifts = Shift.query.filter_by(
            account_id=account_id,
            team_id=team_id
        ).all()
        
        shifts_deleted = len(shifts)
        for shift in shifts:
            print(f"  🗑️ Deleting shift: {shift.date} {shift.current_shift_type}→{shift.next_shift_type}")
            db.session.delete(shift)
        
        # 5. Delete HandoverRequests for this account/team
        handover_requests = HandoverRequest.query.filter_by(
            account_id=account_id,
            team_id=team_id
        ).all()
        
        requests_deleted = len(handover_requests)
        for request in handover_requests:
            print(f"  🗑️ Deleting handover request: {request.id}")
            db.session.delete(request)
        
        # Commit all deletions
        db.session.commit()
        
        print(f"\n✅ Cleanup completed successfully!")
        print(f"   📊 Summary:")
        print(f"   - HandoverNotifications deleted: {notifications_deleted}")
        print(f"   - IncidentAssignments deleted: {assignments_deleted}")
        print(f"   - HandoverResponseLogs deleted: {logs_deleted}")
        print(f"   - Shifts deleted: {shifts_deleted}")
        print(f"   - HandoverRequests deleted: {requests_deleted}")
        print(f"\n🎯 Account 'TechCorp Solutions' and Team 'Operations Team' data cleared!")
        print(f"   Ready for fresh testing! 🚀")
        
    except Exception as e:
        print(f"❌ Error during cleanup: {str(e)}")
        db.session.rollback()
        raise

if __name__ == "__main__":
    with app.app_context():
        cleanup_techcorp_data()