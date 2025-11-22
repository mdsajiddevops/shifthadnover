#!/usr/bin/env python3
"""
Ultimate comprehensive cleanup script to remove all handover reports and notification data 
for Account "TechCorp Solutions" (ID: 1) and Team "Operations Team" (ID: 2)
Handles ALL foreign key constraints including current_shift_engineers.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app, db
from sqlalchemy import text

def cleanup_techcorp_data_ultimate():
    """Clean up all handover data for TechCorp Solutions (Account ID: 1) and Operations Team (Team ID: 2)"""
    
    account_id = 1  # TechCorp Solutions
    team_id = 2     # Operations Team
    
    print(f"🧹 Starting ULTIMATE cleanup for Account ID {account_id} (TechCorp Solutions) and Team ID {team_id} (Operations Team)")
    print("This will handle ALL foreign key constraints including current_shift_engineers!")
    
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
            
            # Get all handover request IDs for this team
            handover_request_ids = db.session.execute(
                text("SELECT id FROM handover_request WHERE team_id = :team_id"),
                {"team_id": team_id}
            ).fetchall()
            
            handover_request_id_list = [row[0] for row in handover_request_ids]
            print(f"📋 Found {len(handover_request_id_list)} handover requests for team {team_id}: {handover_request_id_list}")
            
            total_deleted = 0
            user_ids_str = ','.join(map(str, user_ids)) if user_ids else '0'
            
            # STEP 1: Delete all handover_notifications that reference handover_requests for this team
            handover_notifications_deleted = 0
            if handover_request_id_list:
                handover_request_ids_str = ','.join(map(str, handover_request_id_list))
                handover_notifications_deleted = db.session.execute(
                    text(f"DELETE FROM handover_notification WHERE handover_request_id IN ({handover_request_ids_str})")
                ).rowcount
                db.session.commit()
                print(f"✅ Deleted {handover_notifications_deleted} HandoverNotifications linked to HandoverRequests")
            
            # STEP 2: Delete remaining handover_notifications for users in this team
            user_notifications_deleted = db.session.execute(
                text(f"DELETE FROM handover_notification WHERE recipient_id IN ({user_ids_str})")
            ).rowcount
            db.session.commit()
            total_deleted += (handover_notifications_deleted + user_notifications_deleted)
            print(f"✅ Deleted {user_notifications_deleted} additional HandoverNotifications for team users")
            
            # STEP 3: Delete handover_responses before handover_requests
            responses_deleted = 0
            if handover_request_id_list:
                responses_deleted = db.session.execute(
                    text(f"DELETE FROM handover_response WHERE handover_request_id IN ({handover_request_ids_str})")
                ).rowcount
                db.session.commit()
                total_deleted += responses_deleted
                print(f"✅ Deleted {responses_deleted} HandoverResponses")
            
            # STEP 4: Now safe to delete handover_requests
            handover_requests_deleted = db.session.execute(
                text("DELETE FROM handover_request WHERE team_id = :team_id"),
                {"team_id": team_id}
            ).rowcount
            db.session.commit()
            total_deleted += handover_requests_deleted
            print(f"✅ Deleted {handover_requests_deleted} HandoverRequests")
            
            # STEP 5: Delete IncidentAssignments
            assignments_deleted = db.session.execute(
                text(f"DELETE FROM incident_assignment WHERE assigned_to_id IN ({user_ids_str})")
            ).rowcount
            db.session.commit()
            total_deleted += assignments_deleted
            print(f"✅ Deleted {assignments_deleted} IncidentAssignments")
            
            # STEP 6: Delete HandoverIncidentResponseLogs for this team
            response_logs_deleted = db.session.execute(
                text("DELETE FROM handover_incident_response_log WHERE team_id = :team_id"),
                {"team_id": team_id}
            ).rowcount
            db.session.commit()
            total_deleted += response_logs_deleted
            print(f"✅ Deleted {response_logs_deleted} HandoverIncidentResponseLogs")
            
            # STEP 7: Delete incidents that reference these shifts
            incidents_deleted = 0
            if shift_id_list:
                shift_ids_str = ','.join(map(str, shift_id_list))
                incidents_deleted = db.session.execute(
                    text(f"DELETE FROM incident WHERE shift_id IN ({shift_ids_str})")
                ).rowcount
                db.session.commit()
                total_deleted += incidents_deleted
                print(f"✅ Deleted {incidents_deleted} incidents")
            
            # STEP 8: Delete current_shift_engineers that reference these shifts
            current_shift_engineers_deleted = 0
            if shift_id_list:
                current_shift_engineers_deleted = db.session.execute(
                    text(f"DELETE FROM current_shift_engineers WHERE shift_id IN ({shift_ids_str})")
                ).rowcount
                db.session.commit()
                total_deleted += current_shift_engineers_deleted
                print(f"✅ Deleted {current_shift_engineers_deleted} CurrentShiftEngineers")
            
            # STEP 8b: Delete next_shift_engineers that reference these shifts
            next_shift_engineers_deleted = 0
            if shift_id_list:
                next_shift_engineers_deleted = db.session.execute(
                    text(f"DELETE FROM next_shift_engineers WHERE shift_id IN ({shift_ids_str})")
                ).rowcount
                db.session.commit()
                total_deleted += next_shift_engineers_deleted
                print(f"✅ Deleted {next_shift_engineers_deleted} NextShiftEngineers")
            
            # STEP 9: NOW safe to delete Shifts
            shifts_deleted = 0
            if shift_id_list:
                shifts_deleted = db.session.execute(
                    text(f"DELETE FROM shift WHERE id IN ({shift_ids_str})")
                ).rowcount
                db.session.commit()
                total_deleted += shifts_deleted
                print(f"✅ Deleted {shifts_deleted} Shifts")
            
            # STEP 10: Clean up any remaining notification-related data
            dashboard_notifications_deleted = 0
            try:
                dashboard_notifications_deleted = db.session.execute(
                    text(f"DELETE FROM dashboard_notification WHERE user_id IN ({user_ids_str})")
                ).rowcount
                db.session.commit()
                total_deleted += dashboard_notifications_deleted
                print(f"✅ Deleted {dashboard_notifications_deleted} DashboardNotifications")
            except Exception as e:
                print(f"⚠️ Dashboard notifications table may not exist: {e}")
            
            # STEP 11: Delete any incident notifications for this team
            incident_notifications_deleted = 0
            try:
                incident_notifications_deleted = db.session.execute(
                    text("DELETE FROM incident_notification WHERE team_id = :team_id"),
                    {"team_id": team_id}
                ).rowcount
                db.session.commit()
                total_deleted += incident_notifications_deleted
                print(f"✅ Deleted {incident_notifications_deleted} IncidentNotifications")
            except Exception as e:
                print(f"⚠️ Incident notifications table may not exist: {e}")
            
            print(f"\n🎉 ULTIMATE CLEANUP COMPLETED SUCCESSFULLY! 🎉")
            print(f"📊 Total items deleted: {total_deleted}")
            print(f"   - HandoverNotifications (request-linked): {handover_notifications_deleted}")
            print(f"   - HandoverNotifications (user-linked): {user_notifications_deleted}")
            print(f"   - HandoverResponses: {responses_deleted}")
            print(f"   - HandoverRequests: {handover_requests_deleted}")
            print(f"   - IncidentAssignments: {assignments_deleted}")
            print(f"   - HandoverIncidentResponseLogs: {response_logs_deleted}")
            print(f"   - Incidents: {incidents_deleted}")
            print(f"   - CurrentShiftEngineers: {current_shift_engineers_deleted}")
            print(f"   - NextShiftEngineers: {next_shift_engineers_deleted}")
            print(f"   - Shifts: {shifts_deleted}")
            print(f"   - DashboardNotifications: {dashboard_notifications_deleted}")
            print(f"   - IncidentNotifications: {incident_notifications_deleted}")
            print(f"\n✨ TechCorp Solutions and Operations Team test environment is COMPLETELY CLEAN!")
            print(f"🚀 Ready for fresh testing workflow! All constraints handled properly!")
            
            # Final verification
            print(f"\n🔍 Final Verification:")
            remaining_notifications = db.session.execute(
                text(f"SELECT COUNT(*) FROM handover_notification WHERE recipient_id IN ({user_ids_str})")
            ).scalar()
            
            remaining_request_notifications = 0
            if handover_request_id_list:
                remaining_request_notifications = db.session.execute(
                    text(f"SELECT COUNT(*) FROM handover_notification WHERE handover_request_id IN ({handover_request_ids_str})")
                ).scalar()
            
            remaining_requests = db.session.execute(
                text("SELECT COUNT(*) FROM handover_request WHERE team_id = :team_id"),
                {"team_id": team_id}
            ).scalar()
            
            remaining_shifts = db.session.execute(
                text("SELECT COUNT(*) FROM shift WHERE team_id = :team_id"),
                {"team_id": team_id}
            ).scalar()
            
            remaining_current_shift_engineers = 0
            remaining_next_shift_engineers = 0
            if shift_id_list:
                remaining_current_shift_engineers = db.session.execute(
                    text(f"SELECT COUNT(*) FROM current_shift_engineers WHERE shift_id IN ({shift_ids_str})")
                ).scalar()
                remaining_next_shift_engineers = db.session.execute(
                    text(f"SELECT COUNT(*) FROM next_shift_engineers WHERE shift_id IN ({shift_ids_str})")
                ).scalar()
            
            print(f"   - Remaining HandoverNotifications for team users: {remaining_notifications}")
            print(f"   - Remaining HandoverNotifications for team requests: {remaining_request_notifications}")
            print(f"   - Remaining HandoverRequests for team: {remaining_requests}")
            print(f"   - Remaining CurrentShiftEngineers for team shifts: {remaining_current_shift_engineers}")
            print(f"   - Remaining NextShiftEngineers for team shifts: {remaining_next_shift_engineers}")
            print(f"   - Remaining Shifts for team: {remaining_shifts}")
            
            if (remaining_notifications == 0 and remaining_request_notifications == 0 and 
                remaining_requests == 0 and remaining_shifts == 0 and remaining_current_shift_engineers == 0 and remaining_next_shift_engineers == 0):
                print("✅ PERFECT! ALL targeted data successfully cleaned!")
                print("🚀 Ready for fresh testing workflow!")
            else:
                print("⚠️ Some data may still remain - please check manually")

        except Exception as e:
            print(f"❌ Error during cleanup: {e}")
            db.session.rollback()
            import traceback
            traceback.print_exc()
            raise

if __name__ == "__main__":
    cleanup_techcorp_data_ultimate()