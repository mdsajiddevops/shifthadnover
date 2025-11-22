#!/usr/bin/env python3
"""
Safe TechCorp Cleanup Script - SQL Direct Approach
Cleans TechCorp Solutions (Account ID: 1) and Operations Team (Team ID: 2) data
Uses direct SQL to avoid ORM model mismatches
"""

import sys
sys.path.append('/app')

from app import app, db
from sqlalchemy import text

def safe_cleanup_techcorp():
    """Clean up TechCorp data using direct SQL commands"""
    
    account_id = 1  # TechCorp Solutions
    team_id = 2     # Operations Team
    
    print(f"🧹 Starting SAFE cleanup for Account ID {account_id} (TechCorp Solutions) and Team ID {team_id} (Operations Team)")
    
    with app.app_context():
        try:
            total_deleted = 0
            
            # Get users in the team first
            result = db.session.execute(
                text("SELECT DISTINCT user_id FROM team_member WHERE team_id = :team_id AND user_id IS NOT NULL"),
                {"team_id": team_id}
            )
            user_ids = [row[0] for row in result.fetchall()]
            print(f"📋 Found {len(user_ids)} users in Operations Team: {user_ids}")
            
            if not user_ids:
                print("❌ No users found in Operations Team. Cleanup aborted.")
                return
            
            # Create user_ids string for SQL IN clause
            user_ids_str = ','.join(map(str, user_ids))
            
            # 1. Delete handover notifications for team users
            result = db.session.execute(
                text(f"DELETE FROM handover_notification WHERE recipient_id IN ({user_ids_str})")
            )
            notifications_deleted = result.rowcount
            db.session.commit()
            total_deleted += notifications_deleted
            print(f"✅ Deleted {notifications_deleted} handover_notifications")
            
            # 2. Delete incident assignments for team users  
            result = db.session.execute(
                text(f"DELETE FROM incident_assignment WHERE assigned_to_id IN ({user_ids_str})")
            )
            assignments_deleted = result.rowcount
            db.session.commit()
            total_deleted += assignments_deleted
            print(f"✅ Deleted {assignments_deleted} incident_assignments")
            
            # 3. Delete handover incident response logs for this team
            result = db.session.execute(
                text("DELETE FROM handover_incident_response_log WHERE team_id = :team_id"),
                {"team_id": team_id}
            )
            response_logs_deleted = result.rowcount
            db.session.commit()
            total_deleted += response_logs_deleted
            print(f"✅ Deleted {response_logs_deleted} handover_incident_response_logs")
            
            # 4. Delete shift key points for this team
            result = db.session.execute(
                text("DELETE FROM shift_key_point WHERE account_id = :account_id AND team_id = :team_id"),
                {"account_id": account_id, "team_id": team_id}
            )
            key_points_deleted = result.rowcount
            db.session.commit()
            total_deleted += key_points_deleted
            print(f"✅ Deleted {key_points_deleted} shift_key_points")
            
            # 5. Delete incidents for team shifts
            result = db.session.execute(
                text("DELETE i FROM incident i JOIN shift s ON i.shift_id = s.id WHERE s.account_id = :account_id AND s.team_id = :team_id"),
                {"account_id": account_id, "team_id": team_id}
            )
            incidents_deleted = result.rowcount
            db.session.commit()
            total_deleted += incidents_deleted
            print(f"✅ Deleted {incidents_deleted} incidents")
            
            # 6. Delete handover responses (if table exists and has correct structure)
            try:
                result = db.session.execute(
                    text("DELETE hr FROM handover_response hr JOIN handover_request r ON hr.handover_request_id = r.id WHERE r.team_id = :team_id"),
                    {"team_id": team_id}
                )
                responses_deleted = result.rowcount
                db.session.commit()
                total_deleted += responses_deleted
                print(f"✅ Deleted {responses_deleted} handover_responses")
            except Exception as e:
                print(f"⚠️ Skipping handover_responses (table issue): {str(e)[:100]}...")
                responses_deleted = 0
            
            # 7. Delete handover requests for this team
            result = db.session.execute(
                text("DELETE FROM handover_request WHERE team_id = :team_id"),
                {"team_id": team_id}
            )
            requests_deleted = result.rowcount
            db.session.commit()
            total_deleted += requests_deleted
            print(f"✅ Deleted {requests_deleted} handover_requests")
            
            # 8. Finally delete shifts for this team
            result = db.session.execute(
                text("DELETE FROM shift WHERE account_id = :account_id AND team_id = :team_id"),
                {"account_id": account_id, "team_id": team_id}
            )
            shifts_deleted = result.rowcount
            db.session.commit()
            total_deleted += shifts_deleted
            print(f"✅ Deleted {shifts_deleted} shifts")
            
            print(f"\n🎉 SAFE Cleanup completed successfully!")
            print(f"📊 Total items deleted: {total_deleted}")
            print(f"   - Handover Notifications: {notifications_deleted}")
            print(f"   - Incident Assignments: {assignments_deleted}")
            print(f"   - Response Logs: {response_logs_deleted}")
            print(f"   - Shift Key Points: {key_points_deleted}")
            print(f"   - Incidents: {incidents_deleted}")
            print(f"   - Handover Responses: {responses_deleted}")
            print(f"   - Handover Requests: {requests_deleted}")
            print(f"   - Shifts: {shifts_deleted}")
            print(f"\n✨ TechCorp Solutions - Operations Team is now clean and ready for fresh testing!")

        except Exception as e:
            print(f"❌ Error during cleanup: {e}")
            db.session.rollback()
            raise

if __name__ == "__main__":
    safe_cleanup_techcorp()