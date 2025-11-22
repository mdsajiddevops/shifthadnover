#!/usr/bin/env python3
"""
Ultimate TechCorp Cleanup Script - Handles ALL possible foreign key constraints
Cleans TechCorp Solutions (Account ID: 1) and Operations Team (Team ID: 2) data
Includes current_shift_engineers AND next_shift_engineers tables
"""

import sys
sys.path.append('/app')

from app import app, db
from sqlalchemy import text

def ultimate_cleanup_techcorp():
    """Ultimate cleanup that handles ALL possible foreign key constraints"""
    
    account_id = 1  # TechCorp Solutions
    team_id = 2     # Operations Team
    
    print(f"🧹 Starting ULTIMATE cleanup for Account ID {account_id} (TechCorp Solutions) and Team ID {team_id} (Operations Team)")
    
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
                
                # Delete ALL tables that might reference shift_id
                tables_to_clean = [
                    'current_shift_engineers',
                    'next_shift_engineers',
                    'shift_key_point',
                    'incident'
                ]
                
                for table in tables_to_clean:
                    try:
                        result = db.session.execute(
                            text(f"DELETE FROM {table} WHERE shift_id IN ({shift_ids_str})")
                        )
                        deleted_count = result.rowcount
                        db.session.commit()
                        total_deleted += deleted_count
                        print(f"✅ Deleted {deleted_count} records from {table}")
                    except Exception as e:
                        print(f"⚠️ Could not delete from {table}: {str(e)[:100]}...")
                
                # Now we can safely delete the shifts
                result = db.session.execute(
                    text("DELETE FROM shift WHERE account_id = :account_id AND team_id = :team_id"),
                    {"account_id": account_id, "team_id": team_id}
                )
                shifts_deleted = result.rowcount
                db.session.commit()
                total_deleted += shifts_deleted
                print(f"✅ Deleted {shifts_deleted} shifts")
            else:
                shifts_deleted = 0
                print(f"✅ No shifts found to delete")
            
            # Final verification - check for any remaining data
            remaining_notifications = db.session.execute(
                text("SELECT COUNT(*) FROM handover_notification hn JOIN user u ON hn.recipient_id = u.id WHERE u.account_id = :account_id"),
                {"account_id": account_id}
            ).scalar()
            
            remaining_requests = db.session.execute(
                text("SELECT COUNT(*) FROM handover_request WHERE team_id = :team_id"),
                {"team_id": team_id}
            ).scalar()
            
            remaining_shifts = db.session.execute(
                text("SELECT COUNT(*) FROM shift WHERE account_id = :account_id AND team_id = :team_id"),
                {"account_id": account_id, "team_id": team_id}
            ).scalar()
            
            print(f"\n📊 Final Verification:")
            print(f"   - Remaining handover_notifications for account: {remaining_notifications}")
            print(f"   - Remaining handover_requests for team: {remaining_requests}")
            print(f"   - Remaining shifts for team: {remaining_shifts}")
            
            if remaining_notifications == 0 and remaining_requests == 0 and remaining_shifts == 0:
                print(f"\n🎉 ULTIMATE Cleanup SUCCESS! All TechCorp data cleaned!")
                print(f"📊 Total items deleted in this final run: {total_deleted}")
                print(f"✨ TechCorp Solutions - Operations Team is now completely clean!")
                print(f"🚀 Ready for fresh testing with testuser1, testuser2, testuser3!")
            else:
                print(f"\n⚠️ Some data may remain. Check the verification counts above.")

        except Exception as e:
            print(f"❌ Error during cleanup: {e}")
            db.session.rollback()
            raise

if __name__ == "__main__":
    ultimate_cleanup_techcorp()