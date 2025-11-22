#!/usr/bin/env python3
import sys
import os
sys.path.append("/app")

# Set environment variable for database URL
os.environ["LOCAL_DEVELOPMENT"] = "false"

try:
    from app import app, db
    from models.models import Shift, Incident, ShiftKeyPoint
    from models.handover_enhanced import HandoverRequest, HandoverNotification, IncidentAssignment, HandoverIncidentResponseLog
    from sqlalchemy import text
    
    def cleanup_techcorp():
        print("🧹 Starting TechCorp cleanup from within container...")
        
        with app.app_context():
            try:
                account_id = 1  # TechCorp Solutions
                team_id = 2     # Operations Team
                
                print(f"Cleaning data for Account ID: {account_id}, Team ID: {team_id}")
                
                # Get user IDs for TechCorp
                user_ids = db.session.execute(
                    text("SELECT id FROM users WHERE account_id = :account_id"),
                    {"account_id": account_id}
                ).fetchall()
                user_id_list = [row[0] for row in user_ids]
                print(f"Found {len(user_id_list)} users in TechCorp: {user_id_list}")
                
                # Get shift IDs for Operations team
                shift_ids = db.session.execute(
                    text("SELECT id FROM shifts WHERE account_id = :account_id AND team_id = :team_id"),
                    {"account_id": account_id, "team_id": team_id}
                ).fetchall()
                shift_id_list = [row[0] for row in shift_ids]
                print(f"Found {len(shift_id_list)} shifts for Operations team: {shift_id_list}")
                
                total_deleted = 0
                
                # 1. Delete HandoverNotifications
                if user_id_list:
                    deleted = db.session.execute(
                        text("DELETE FROM handover_notifications WHERE recipient_id IN :user_ids"),
                        {"user_ids": tuple(user_id_list) if len(user_id_list) > 1 else (user_id_list[0],)}
                    ).rowcount
                    db.session.commit()
                    print(f"Deleted {deleted} handover notifications")
                    total_deleted += deleted
                
                # 2. Delete IncidentAssignments
                if user_id_list:
                    deleted = db.session.execute(
                        text("DELETE FROM incident_assignments WHERE assigned_to_id IN :user_ids"),
                        {"user_ids": tuple(user_id_list) if len(user_id_list) > 1 else (user_id_list[0],)}
                    ).rowcount
                    db.session.commit()
                    print(f"Deleted {deleted} incident assignments")
                    total_deleted += deleted
                
                # 3. Delete HandoverIncidentResponseLogs
                deleted = db.session.execute(
                    text("DELETE FROM handover_incident_response_logs WHERE team_id = :team_id"),
                    {"team_id": team_id}
                ).rowcount
                db.session.commit()
                print(f"Deleted {deleted} response logs")
                total_deleted += deleted
                
                # 4. Delete ShiftKeyPoints
                deleted = db.session.execute(
                    text("DELETE FROM shift_key_points WHERE account_id = :account_id AND team_id = :team_id"),
                    {"account_id": account_id, "team_id": team_id}
                ).rowcount
                db.session.commit()
                print(f"Deleted {deleted} shift key points")
                total_deleted += deleted
                
                # 5. Delete Incidents
                if shift_id_list:
                    deleted = db.session.execute(
                        text("DELETE FROM incidents WHERE shift_id IN :shift_ids"),
                        {"shift_ids": tuple(shift_id_list) if len(shift_id_list) > 1 else (shift_id_list[0],)}
                    ).rowcount
                    db.session.commit()
                    print(f"Deleted {deleted} incidents")
                    total_deleted += deleted
                
                # 6. Delete HandoverRequests
                deleted = db.session.execute(
                    text("DELETE FROM handover_requests WHERE team_id = :team_id"),
                    {"team_id": team_id}
                ).rowcount
                db.session.commit()
                print(f"Deleted {deleted} handover requests")
                total_deleted += deleted
                
                # 7. Delete Shifts
                if shift_id_list:
                    deleted = db.session.execute(
                        text("DELETE FROM shifts WHERE account_id = :account_id AND team_id = :team_id"),
                        {"account_id": account_id, "team_id": team_id}
                    ).rowcount
                    db.session.commit()
                    print(f"Deleted {deleted} shifts")
                    total_deleted += deleted
                
                print(f"\n🎉 Cleanup completed! Total items deleted: {total_deleted}")
                return True
                
            except Exception as e:
                print(f"❌ Error during cleanup: {e}")
                db.session.rollback()
                return False
    
    if __name__ == "__main__":
        success = cleanup_techcorp()
        sys.exit(0 if success else 1)
        
except ImportError as e:
    print(f"Import error: {e}")
    sys.exit(1)
except Exception as e:
    print(f"Error: {e}")
    sys.exit(1)

