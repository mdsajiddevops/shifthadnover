#!/usr/bin/env python3
"""
Final TechCorp Cleanup Script - Handles ALL foreign key constraints
Cleans TechCorp Solutions (Account ID: 1) and Operations Team (Team ID: 2) data
Includes current_shift_engineers table
"""

import sys
sys.path.append('/app')

from app import app, db
from sqlalchemy import text

def final_cleanup_techcorp():
    """Final cleanup that handles ALL foreign key constraints"""
    
    account_id = 1  # TechCorp Solutions
    team_id = 2     # Operations Team
    
    print(f"🧹 Starting FINAL cleanup for Account ID {account_id} (TechCorp Solutions) and Team ID {team_id} (Operations Team)")
    
    with app.app_context():
        try:
            total_deleted = 0
            
            # Get all shift IDs for this team before we start deleting
            shifts_result = db.session.execute(
                text("SELECT id FROM shift WHERE account_id = :account_id AND team_id = :team_id"),
                {"account_id": account_id, "team_id": team_id}
            )
            shift_ids = [row[0] for row in shifts_result.fetchall()]
            print(f"📋 Found {len(shift_ids)} shifts: {shift_ids}")
            
            if shift_ids:
                shift_ids_str = ','.join(map(str, shift_ids))
                
                # 1. Delete current_shift_engineers that reference these shifts
                result = db.session.execute(
                    text(f"DELETE FROM current_shift_engineers WHERE shift_id IN ({shift_ids_str})")
                )
                engineers_deleted = result.rowcount
                db.session.commit()
                total_deleted += engineers_deleted
                print(f"✅ Deleted {engineers_deleted} current_shift_engineers")
                
                # 2. Delete shift key points for these shifts
                result = db.session.execute(
                    text(f"DELETE FROM shift_key_point WHERE shift_id IN ({shift_ids_str})")
                )
                key_points_deleted = result.rowcount
                db.session.commit()
                total_deleted += key_points_deleted
                print(f"✅ Deleted {key_points_deleted} shift_key_points")
                
                # 3. Delete incidents for these shifts
                result = db.session.execute(
                    text(f"DELETE FROM incident WHERE shift_id IN ({shift_ids_str})")
                )
                incidents_deleted = result.rowcount
                db.session.commit()
                total_deleted += incidents_deleted
                print(f"✅ Deleted {incidents_deleted} incidents")
                
                # 4. Now we can safely delete the shifts
                result = db.session.execute(
                    text("DELETE FROM shift WHERE account_id = :account_id AND team_id = :team_id"),
                    {"account_id": account_id, "team_id": team_id}
                )
                shifts_deleted = result.rowcount
                db.session.commit()
                total_deleted += shifts_deleted
                print(f"✅ Deleted {shifts_deleted} shifts")
            else:
                engineers_deleted = 0
                key_points_deleted = 0
                incidents_deleted = 0
                shifts_deleted = 0
                print(f"✅ No shifts found to delete")
            
            # 5. Check for any remaining handover data
            remaining_notifications = db.session.execute(
                text("SELECT COUNT(*) FROM handover_notification hn JOIN user u ON hn.recipient_id = u.id WHERE u.account_id = :account_id"),
                {"account_id": account_id}
            ).scalar()
            
            remaining_requests = db.session.execute(
                text("SELECT COUNT(*) FROM handover_request WHERE team_id = :team_id"),
                {"team_id": team_id}
            ).scalar()
            
            print(f"\n📊 Verification:")
            print(f"   - Remaining handover_notifications for account: {remaining_notifications}")
            print(f"   - Remaining handover_requests for team: {remaining_requests}")
            
            print(f"\n🎉 FINAL Cleanup completed successfully!")
            print(f"📊 Total items deleted in this run: {total_deleted}")
            print(f"   - Current Shift Engineers: {engineers_deleted}")
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
    final_cleanup_techcorp()