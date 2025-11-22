#!/usr/bin/env python3
"""
Comprehensive cleanup script to remove all handover reports and notification data 
for Account "TechCorp Solutions" (ID: 1) and Team "Operations Team" (ID: 2)
Handles database schema issues and foreign key constraints by using direct SQL.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app, db
from sqlalchemy import text

def cleanup_techcorp_data_safe():
    """Clean up all handover data for TechCorp Solutions (Account ID: 1) and Operations Team (Team ID: 2)"""
    
    account_id = 1  # TechCorp Solutions
    team_id = 2     # Operations Team
    
    print(f"🧹 Starting safe cleanup for Account ID {account_id} (TechCorp Solutions) and Team ID {team_id} (Operations Team)")
    
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
            
            # 1. Delete HandoverNotifications using direct SQL
            user_ids_str = ','.join(map(str, user_ids))
            notifications_deleted = db.session.execute(
                text(f"DELETE FROM handover_notification WHERE recipient_id IN ({user_ids_str})")
            ).rowcount
            db.session.commit()
            total_deleted += notifications_deleted
            print(f"✅ Deleted {notifications_deleted} HandoverNotifications")
            
            # 2. Delete IncidentAssignments using direct SQL
            assignments_deleted = db.session.execute(
                text(f"DELETE FROM incident_assignment WHERE assigned_to_id IN ({user_ids_str})")
            ).rowcount
            db.session.commit()
            total_deleted += assignments_deleted
            print(f"✅ Deleted {assignments_deleted} IncidentAssignments")
            
            # 3. Delete HandoverIncidentResponseLogs for this team
            response_logs_deleted = db.session.execute(
                text("DELETE FROM handover_incident_response_log WHERE team_id = :team_id"),
                {"team_id": team_id}
            ).rowcount
            db.session.commit()
            total_deleted += response_logs_deleted
            print(f"✅ Deleted {response_logs_deleted} HandoverIncidentResponseLogs")
            
            # 4. Delete handover_response records first (to avoid foreign key issues)
            handover_request_ids = db.session.execute(
                text("SELECT id FROM handover_request WHERE team_id = :team_id"),
                {"team_id": team_id}
            ).fetchall()
            
            handover_request_id_list = [row[0] for row in handover_request_ids]
            
            if handover_request_id_list:
                handover_request_ids_str = ','.join(map(str, handover_request_id_list))
                
                # Delete handover responses first
                responses_deleted = db.session.execute(
                    text(f"DELETE FROM handover_response WHERE handover_request_id IN ({handover_request_ids_str})")
                ).rowcount
                db.session.commit()
                total_deleted += responses_deleted
                print(f"✅ Deleted {responses_deleted} HandoverResponses")
            
            # 5. Delete HandoverRequests for this team using direct SQL
            handover_requests_deleted = db.session.execute(
                text("DELETE FROM handover_request WHERE team_id = :team_id"),
                {"team_id": team_id}
            ).rowcount
            db.session.commit()
            total_deleted += handover_requests_deleted
            print(f"✅ Deleted {handover_requests_deleted} HandoverRequests")
            
            # 6. Delete incidents that reference these shifts
            incidents_deleted = 0
            if shift_id_list:
                shift_ids_str = ','.join(map(str, shift_id_list))
                incidents_deleted = db.session.execute(
                    text(f"DELETE FROM incident WHERE shift_id IN ({shift_ids_str})")
                ).rowcount
                db.session.commit()
                total_deleted += incidents_deleted
                print(f"✅ Deleted {incidents_deleted} incidents")
            
            # 7. Finally delete Shifts
            shifts_deleted = 0
            if shift_id_list:
                shifts_deleted = db.session.execute(
                    text(f"DELETE FROM shift WHERE id IN ({shift_ids_str})")
                ).rowcount
                db.session.commit()
                total_deleted += shifts_deleted
                print(f"✅ Deleted {shifts_deleted} Shifts")
            
            # 8. Clean up any remaining notification-related data
            # Delete dashboard notifications for these users
            dashboard_notifications_deleted = db.session.execute(
                text(f"DELETE FROM dashboard_notification WHERE user_id IN ({user_ids_str})")
            ).rowcount
            db.session.commit()
            total_deleted += dashboard_notifications_deleted
            print(f"✅ Deleted {dashboard_notifications_deleted} DashboardNotifications")
            
            # Delete any incident notifications for this team
            incident_notifications_deleted = db.session.execute(
                text("DELETE FROM incident_notification WHERE team_id = :team_id"),
                {"team_id": team_id}
            ).rowcount
            db.session.commit()
            total_deleted += incident_notifications_deleted
            print(f"✅ Deleted {incident_notifications_deleted} IncidentNotifications")
            
            print(f"\n🎉 Cleanup completed successfully!")
            print(f"📊 Total items deleted: {total_deleted}")
            print(f"   - HandoverNotifications: {notifications_deleted}")
            print(f"   - IncidentAssignments: {assignments_deleted}")
            print(f"   - HandoverIncidentResponseLogs: {response_logs_deleted}")
            print(f"   - HandoverResponses: {responses_deleted if handover_request_id_list else 0}")
            print(f"   - HandoverRequests: {handover_requests_deleted}")
            print(f"   - Incidents: {incidents_deleted}")
            print(f"   - Shifts: {shifts_deleted}")
            print(f"   - DashboardNotifications: {dashboard_notifications_deleted}")
            print(f"   - IncidentNotifications: {incident_notifications_deleted}")
            print(f"\n✨ TechCorp Solutions and Operations Team test environment is now clean and ready for fresh testing!")
            
            # Verify cleanup
            print(f"\n🔍 Verification:")
            remaining_notifications = db.session.execute(
                text(f"SELECT COUNT(*) FROM handover_notification WHERE recipient_id IN ({user_ids_str})")
            ).scalar()
            
            remaining_requests = db.session.execute(
                text("SELECT COUNT(*) FROM handover_request WHERE team_id = :team_id"),
                {"team_id": team_id}
            ).scalar()
            
            remaining_shifts = db.session.execute(
                text("SELECT COUNT(*) FROM shift WHERE team_id = :team_id"),
                {"team_id": team_id}
            ).scalar()
            
            print(f"   - Remaining HandoverNotifications for Operations Team users: {remaining_notifications}")
            print(f"   - Remaining HandoverRequests for Operations Team: {remaining_requests}")
            print(f"   - Remaining Shifts for Operations Team: {remaining_shifts}")
            
            if remaining_notifications == 0 and remaining_requests == 0 and remaining_shifts == 0:
                print("✅ Verification passed: All targeted data successfully cleaned!")
            else:
                print("⚠️ Some data may still remain - please check manually")

        except Exception as e:
            print(f"❌ Error during cleanup: {e}")
            db.session.rollback()
            raise

if __name__ == "__main__":
    cleanup_techcorp_data_safe()