#!/usr/bin/env python3
"""
Complete TechCorp Cleanup Script - Handles all foreign key constraints
Cleans TechCorp Solutions (Account ID: 1) and Operations Team (Team ID: 2) data
Uses proper order to handle foreign key constraints
"""

import sys
sys.path.append('/app')

from app import app, db
from sqlalchemy import text

def complete_cleanup_techcorp():
    """Clean up TechCorp data handling all foreign key constraints properly"""
    
    account_id = 1  # TechCorp Solutions
    team_id = 2     # Operations Team
    
    print(f"🧹 Starting COMPLETE cleanup for Account ID {account_id} (TechCorp Solutions) and Team ID {team_id} (Operations Team)")
    
    with app.app_context():
        try:
            total_deleted = 0
            
            # First, let's see what handover_requests exist for this team
            requests_result = db.session.execute(
                text("SELECT id, created_by_id FROM handover_request WHERE team_id = :team_id"),
                {"team_id": team_id}
            )
            request_ids = [row[0] for row in requests_result.fetchall()]
            print(f"📋 Found {len(request_ids)} handover_requests: {request_ids}")
            
            if request_ids:
                # Create request_ids string for SQL IN clause
                request_ids_str = ','.join(map(str, request_ids))
                
                # 1. Delete handover notifications that reference these requests
                result = db.session.execute(
                    text(f"DELETE FROM handover_notification WHERE handover_request_id IN ({request_ids_str})")
                )
                notifications_deleted = result.rowcount
                db.session.commit()
                total_deleted += notifications_deleted
                print(f"✅ Deleted {notifications_deleted} handover_notifications (referencing requests)")
            else:
                notifications_deleted = 0
                print(f"✅ No handover_requests found, skipping notifications")
            
            # 2. Delete remaining handover notifications for team users
            result = db.session.execute(
                text("DELETE hn FROM handover_notification hn JOIN user u ON hn.recipient_id = u.id WHERE u.account_id = :account_id"),
                {"account_id": account_id}
            )
            remaining_notifications = result.rowcount
            db.session.commit()
            total_deleted += remaining_notifications
            notifications_deleted += remaining_notifications
            print(f"✅ Deleted {remaining_notifications} remaining handover_notifications")
            
            # 3. Delete incident assignments for team users  
            result = db.session.execute(
                text("DELETE ia FROM incident_assignment ia JOIN user u ON ia.assigned_to_id = u.id WHERE u.account_id = :account_id"),
                {"account_id": account_id}
            )
            assignments_deleted = result.rowcount
            db.session.commit()
            total_deleted += assignments_deleted
            print(f"✅ Deleted {assignments_deleted} incident_assignments")
            
            # 4. Delete handover incident response logs for this team
            result = db.session.execute(
                text("DELETE FROM handover_incident_response_log WHERE team_id = :team_id"),
                {"team_id": team_id}
            )
            response_logs_deleted = result.rowcount
            db.session.commit()
            total_deleted += response_logs_deleted
            print(f"✅ Deleted {response_logs_deleted} handover_incident_response_logs")
            
            # 5. Delete handover responses (if they exist and reference requests)
            if request_ids:
                try:
                    result = db.session.execute(
                        text(f"DELETE FROM handover_response WHERE handover_request_id IN ({request_ids_str})")
                    )
                    responses_deleted = result.rowcount
                    db.session.commit()
                    total_deleted += responses_deleted
                    print(f"✅ Deleted {responses_deleted} handover_responses")
                except Exception as e:
                    print(f"⚠️ Skipping handover_responses (table issue): {str(e)[:100]}...")
                    responses_deleted = 0
            else:
                responses_deleted = 0
                print(f"✅ No handover_requests, skipping handover_responses")
            
            # 6. Now we can safely delete handover requests
            if request_ids:
                result = db.session.execute(
                    text("DELETE FROM handover_request WHERE team_id = :team_id"),
                    {"team_id": team_id}
                )
                requests_deleted = result.rowcount
                db.session.commit()
                total_deleted += requests_deleted
                print(f"✅ Deleted {requests_deleted} handover_requests")
            else:
                requests_deleted = 0
                print(f"✅ No handover_requests to delete")
            
            # 7. Delete shift key points for this team
            result = db.session.execute(
                text("DELETE FROM shift_key_point WHERE account_id = :account_id AND team_id = :team_id"),
                {"account_id": account_id, "team_id": team_id}
            )
            key_points_deleted = result.rowcount
            db.session.commit()
            total_deleted += key_points_deleted
            print(f"✅ Deleted {key_points_deleted} shift_key_points")
            
            # 8. Delete incidents for team shifts
            result = db.session.execute(
                text("DELETE i FROM incident i JOIN shift s ON i.shift_id = s.id WHERE s.account_id = :account_id AND s.team_id = :team_id"),
                {"account_id": account_id, "team_id": team_id}
            )
            incidents_deleted = result.rowcount
            db.session.commit()
            total_deleted += incidents_deleted
            print(f"✅ Deleted {incidents_deleted} incidents")
            
            # 9. Finally delete shifts for this team
            result = db.session.execute(
                text("DELETE FROM shift WHERE account_id = :account_id AND team_id = :team_id"),
                {"account_id": account_id, "team_id": team_id}
            )
            shifts_deleted = result.rowcount
            db.session.commit()
            total_deleted += shifts_deleted
            print(f"✅ Deleted {shifts_deleted} shifts")
            
            print(f"\n🎉 COMPLETE Cleanup finished successfully!")
            print(f"📊 Total items deleted: {total_deleted}")
            print(f"   - Handover Notifications: {notifications_deleted}")
            print(f"   - Incident Assignments: {assignments_deleted}")
            print(f"   - Response Logs: {response_logs_deleted}")
            print(f"   - Handover Responses: {responses_deleted}")
            print(f"   - Handover Requests: {requests_deleted}")
            print(f"   - Shift Key Points: {key_points_deleted}")
            print(f"   - Incidents: {incidents_deleted}")
            print(f"   - Shifts: {shifts_deleted}")
            print(f"\n✨ TechCorp Solutions - Operations Team is now completely clean!")
            print(f"🚀 Ready for fresh testing with testuser1, testuser2, testuser3!")

        except Exception as e:
            print(f"❌ Error during cleanup: {e}")
            db.session.rollback()
            raise

if __name__ == "__main__":
    complete_cleanup_techcorp()