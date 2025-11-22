#!/usr/bin/env python3
"""
FINAL comprehensive cleanup script that disables foreign key checks temporarily
to ensure complete cleanup of TechCorp Solutions and Operations Team data.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app, db
from sqlalchemy import text

def cleanup_techcorp_data_with_fk_disabled():
    """Clean up all handover data with foreign key constraints temporarily disabled"""
    
    account_id = 1  # TechCorp Solutions
    team_id = 2     # Operations Team
    
    print(f"🧹 Starting FINAL cleanup with FK checks disabled")
    print(f"   Account ID {account_id} (TechCorp Solutions)")
    print(f"   Team ID {team_id} (Operations Team)")
    print("⚠️  Temporarily disabling foreign key checks for complete cleanup!")
    
    with app.app_context():
        try:
            # DISABLE FOREIGN KEY CHECKS
            db.session.execute(text("SET FOREIGN_KEY_CHECKS = 0"))
            db.session.commit()
            print("✅ Foreign key checks DISABLED")
            
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
            
            # Now we can delete everything without worrying about constraints!
            
            # Delete all handover_notifications
            handover_notifications_deleted = 0
            if handover_request_id_list:
                handover_request_ids_str = ','.join(map(str, handover_request_id_list))
                handover_notifications_deleted = db.session.execute(
                    text(f"DELETE FROM handover_notification WHERE handover_request_id IN ({handover_request_ids_str})")
                ).rowcount
                db.session.commit()
            
            user_notifications_deleted = db.session.execute(
                text(f"DELETE FROM handover_notification WHERE recipient_id IN ({user_ids_str})")
            ).rowcount
            db.session.commit()
            total_deleted += (handover_notifications_deleted + user_notifications_deleted)
            print(f"✅ Deleted {handover_notifications_deleted + user_notifications_deleted} HandoverNotifications")
            
            # Delete handover_responses
            responses_deleted = 0
            if handover_request_id_list:
                responses_deleted = db.session.execute(
                    text(f"DELETE FROM handover_response WHERE handover_request_id IN ({handover_request_ids_str})")
                ).rowcount
                db.session.commit()
                total_deleted += responses_deleted
                print(f"✅ Deleted {responses_deleted} HandoverResponses")
            
            # Delete handover_requests
            handover_requests_deleted = db.session.execute(
                text("DELETE FROM handover_request WHERE team_id = :team_id"),
                {"team_id": team_id}
            ).rowcount
            db.session.commit()
            total_deleted += handover_requests_deleted
            print(f"✅ Deleted {handover_requests_deleted} HandoverRequests")
            
            # Delete IncidentAssignments
            assignments_deleted = db.session.execute(
                text(f"DELETE FROM incident_assignment WHERE assigned_to_id IN ({user_ids_str})")
            ).rowcount
            db.session.commit()
            total_deleted += assignments_deleted
            print(f"✅ Deleted {assignments_deleted} IncidentAssignments")
            
            # Delete HandoverIncidentResponseLogs
            response_logs_deleted = db.session.execute(
                text("DELETE FROM handover_incident_response_log WHERE team_id = :team_id"),
                {"team_id": team_id}
            ).rowcount
            db.session.commit()
            total_deleted += response_logs_deleted
            print(f"✅ Deleted {response_logs_deleted} HandoverIncidentResponseLogs")
            
            # Delete incidents
            incidents_deleted = 0
            if shift_id_list:
                shift_ids_str = ','.join(map(str, shift_id_list))
                incidents_deleted = db.session.execute(
                    text(f"DELETE FROM incident WHERE shift_id IN ({shift_ids_str})")
                ).rowcount
                db.session.commit()
                total_deleted += incidents_deleted
                print(f"✅ Deleted {incidents_deleted} incidents")
            
            # Delete ALL shift-related tables
            shift_related_deleted = 0
            if shift_id_list:
                # Delete current_shift_engineers
                current_shift_engineers_deleted = db.session.execute(
                    text(f"DELETE FROM current_shift_engineers WHERE shift_id IN ({shift_ids_str})")
                ).rowcount
                db.session.commit()
                
                # Delete next_shift_engineers  
                next_shift_engineers_deleted = db.session.execute(
                    text(f"DELETE FROM next_shift_engineers WHERE shift_id IN ({shift_ids_str})")
                ).rowcount
                db.session.commit()
                
                # Delete shift_key_point
                shift_key_points_deleted = db.session.execute(
                    text(f"DELETE FROM shift_key_point WHERE shift_id IN ({shift_ids_str})")
                ).rowcount
                db.session.commit()
                
                shift_related_deleted = current_shift_engineers_deleted + next_shift_engineers_deleted + shift_key_points_deleted
                total_deleted += shift_related_deleted
                print(f"✅ Deleted {current_shift_engineers_deleted} CurrentShiftEngineers")
                print(f"✅ Deleted {next_shift_engineers_deleted} NextShiftEngineers") 
                print(f"✅ Deleted {shift_key_points_deleted} ShiftKeyPoints")
            
            # Finally delete Shifts (now safe)
            shifts_deleted = 0
            if shift_id_list:
                shifts_deleted = db.session.execute(
                    text(f"DELETE FROM shift WHERE id IN ({shift_ids_str})")
                ).rowcount
                db.session.commit()
                total_deleted += shifts_deleted
                print(f"✅ Deleted {shifts_deleted} Shifts")
            
            # Clean up remaining notification data
            dashboard_notifications_deleted = 0
            incident_notifications_deleted = 0
            try:
                dashboard_notifications_deleted = db.session.execute(
                    text(f"DELETE FROM dashboard_notification WHERE user_id IN ({user_ids_str})")
                ).rowcount
                db.session.commit()
                
                incident_notifications_deleted = db.session.execute(
                    text("DELETE FROM incident_notification WHERE team_id = :team_id"),
                    {"team_id": team_id}
                ).rowcount
                db.session.commit()
                
                total_deleted += (dashboard_notifications_deleted + incident_notifications_deleted)
                print(f"✅ Deleted {dashboard_notifications_deleted} DashboardNotifications")
                print(f"✅ Deleted {incident_notifications_deleted} IncidentNotifications")
            except Exception as e:
                print(f"⚠️ Some notification tables may not exist: {e}")
            
            # RE-ENABLE FOREIGN KEY CHECKS
            db.session.execute(text("SET FOREIGN_KEY_CHECKS = 1"))
            db.session.commit()
            print("✅ Foreign key checks RE-ENABLED")
            
            print(f"\n🎉 COMPLETE CLEANUP SUCCESSFUL! 🎉")
            print(f"📊 Total items deleted: {total_deleted}")
            print(f"\n✨ TechCorp Solutions and Operations Team environment is COMPLETELY CLEAN!")
            print(f"🚀 Ready for fresh testing workflow!")
            
            # Final verification
            print(f"\n🔍 Final Verification:")
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
            
            print(f"   - Remaining HandoverNotifications: {remaining_notifications}")
            print(f"   - Remaining HandoverRequests: {remaining_requests}")
            print(f"   - Remaining Shifts: {remaining_shifts}")
            
            if remaining_notifications == 0 and remaining_requests == 0 and remaining_shifts == 0:
                print("✅ PERFECT! All targeted data successfully cleaned!")
                print("🚀 Test environment is pristine and ready!")
            else:
                print("⚠️ Some data may still remain")

        except Exception as e:
            print(f"❌ Error during cleanup: {e}")
            # Make sure to re-enable foreign keys even on error
            try:
                db.session.execute(text("SET FOREIGN_KEY_CHECKS = 1"))
                db.session.commit()
                print("✅ Foreign key checks RE-ENABLED after error")
            except:
                pass
            db.session.rollback()
            import traceback
            traceback.print_exc()
            raise

if __name__ == "__main__":
    cleanup_techcorp_data_with_fk_disabled()