#!/usr/bin/env python3
"""
Comprehensive cleanup script to remove all handover reports and notification data 
for Account "TechCorp Solutions" (ID: 1) and Team "Operations Team" (ID: 2)
Handles foreign key constraints by deleting in proper order.
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
    
    print(f"🧹 Starting comprehensive cleanup for Account ID {account_id} (TechCorp Solutions) and Team ID {team_id} (Operations Team)")
    
    with app.app_context():
        try:
            # Get all user IDs from team members for the Operations Team
            team_member_user_ids = db.session.execute(
                text("SELECT DISTINCT user_id FROM team_member WHERE team_id = :team_id AND user_id IS NOT NULL"),
                {"team_id": team_id}
            ).fetchall()
            
            user_ids = [row[0] for row in team_member_user_ids if row[0]]
            print(f"📋 Found {len(user_ids)} users in Operations Team: {user_ids}")
            
            if not user_ids:
                print("❌ No users found in Operations Team. Cleanup aborted.")
                return
            
            # Get all shift IDs for this team
            shift_ids = db.session.execute(
                text("SELECT DISTINCT id FROM shift WHERE team_id = :team_id"),
                {"team_id": team_id}
            ).fetchall()
            
            shift_id_list = [row[0] for row in shift_ids if row[0]]
            print(f"📅 Found {len(shift_id_list)} shifts for team {team_id}: {shift_id_list}")
            
            total_deleted = 0
            
            # 1. Delete HandoverNotifications first (no dependencies)
            notifications_deleted = 0
            notifications = HandoverNotification.query.filter(
                HandoverNotification.recipient_id.in_(user_ids)
            ).all()
            
            for notification in notifications:
                print(f"  🗑️ Deleting notification: {notification.title} for user {notification.recipient_id}")
                db.session.delete(notification)
                notifications_deleted += 1
            
            db.session.commit()
            total_deleted += notifications_deleted
            print(f"✅ Deleted {notifications_deleted} HandoverNotifications")
            
            # 2. Delete IncidentAssignments
            assignments_deleted = 0
            assignments = IncidentAssignment.query.filter(
                IncidentAssignment.assigned_to_id.in_(user_ids)
            ).all()
            
            for assignment in assignments:
                print(f"  🗑️ Deleting assignment: {assignment.incident_title} assigned to user {assignment.assigned_to_id}")
                db.session.delete(assignment)
                assignments_deleted += 1
            
            db.session.commit()
            total_deleted += assignments_deleted
            print(f"✅ Deleted {assignments_deleted} IncidentAssignments")
            
            # 3. Delete HandoverIncidentResponseLogs for this team
            response_logs_deleted = 0
            response_logs = HandoverIncidentResponseLog.query.filter(
                HandoverIncidentResponseLog.team_id == team_id
            ).all()
            
            for log in response_logs:
                print(f"  🗑️ Deleting response log: {log.incident_title}")
                db.session.delete(log)
                response_logs_deleted += 1
            
            db.session.commit()
            total_deleted += response_logs_deleted
            print(f"✅ Deleted {response_logs_deleted} HandoverIncidentResponseLogs")
            
            # 4. Delete incidents that reference these shifts (to avoid foreign key constraint)
            incidents_deleted = 0
            if shift_id_list:
                incidents_deleted = db.session.execute(
                    text("DELETE FROM incident WHERE shift_id IN :shift_ids"),
                    {"shift_ids": tuple(shift_id_list)}
                ).rowcount
                
                db.session.commit()
                total_deleted += incidents_deleted
                print(f"✅ Deleted {incidents_deleted} incidents")
            
            # 5. Delete HandoverRequests for this team
            handover_requests_deleted = 0
            handover_requests = HandoverRequest.query.filter(
                HandoverRequest.team_id == team_id
            ).all()
            
            for request in handover_requests:
                print(f"  🗑️ Deleting handover request from user {request.created_by_id}")
                db.session.delete(request)
                handover_requests_deleted += 1
            
            db.session.commit()
            total_deleted += handover_requests_deleted
            print(f"✅ Deleted {handover_requests_deleted} HandoverRequests")
            
            # 6. Finally delete Shifts (now that incidents are gone)
            shifts_deleted = 0
            if shift_id_list:
                shifts = Shift.query.filter(Shift.id.in_(shift_id_list)).all()
                
                for shift in shifts:
                    print(f"  🗑️ Deleting shift: {shift.date} {shift.current_shift_type}→{shift.next_shift_type}")
                    db.session.delete(shift)
                    shifts_deleted += 1
                
                db.session.commit()
                total_deleted += shifts_deleted
                print(f"✅ Deleted {shifts_deleted} Shifts")
            
            print(f"\n🎉 Cleanup completed successfully!")
            print(f"📊 Total items deleted: {total_deleted}")
            print(f"   - HandoverNotifications: {notifications_deleted}")
            print(f"   - IncidentAssignments: {assignments_deleted}")
            print(f"   - HandoverIncidentResponseLogs: {response_logs_deleted}")
            print(f"   - Incidents: {incidents_deleted}")
            print(f"   - HandoverRequests: {handover_requests_deleted}")
            print(f"   - Shifts: {shifts_deleted}")
            print(f"\n✨ TechCorp Solutions test environment is now clean and ready for fresh testing!")

        except Exception as e:
            print(f"❌ Error during cleanup: {e}")
            db.session.rollback()
            raise

if __name__ == "__main__":
    cleanup_techcorp_data()