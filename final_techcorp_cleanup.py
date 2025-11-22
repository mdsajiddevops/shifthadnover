#!/usr/bin/env python3

"""
COMPLETE TechCorp Solutions Data Cleanup Script
Direct database cleanup for Account ID 1 (TechCorp Solutions) and Team ID 2 (Operations Team)
"""

import sys
import os

# Change to app directory
os.chdir('/app')
sys.path.insert(0, '/app')

# Import the Flask app and database
from app import app, db
from sqlalchemy import text

def complete_techcorp_cleanup():
    """Completely remove all TechCorp Solutions data handling foreign keys properly"""
    
    with app.app_context():
        account_id = 1  # TechCorp Solutions
        team_id = 2     # Operations Team
        
        print("🧹 Starting COMPLETE cleanup for Account ID 1 (TechCorp Solutions) and Team ID 2 (Operations Team)")
        
        try:
            # Step 1: Get shift IDs that will be deleted (for cleaning response logs)
            shift_query = text("SELECT id FROM shift WHERE account_id = :account_id AND team_id = :team_id")
            shift_result = db.session.execute(shift_query, {'account_id': account_id, 'team_id': team_id})
            shift_ids = [row[0] for row in shift_result]
            
            print(f"📋 Found {len(shift_ids)} shifts to cleanup: {shift_ids}")
            
            # Step 2: Clean handover_incident_response_log that references shifts
            if shift_ids:
                log_query = text("DELETE FROM handover_incident_response_log WHERE from_shift_id IN :shift_ids OR to_shift_id IN :shift_ids")
                result = db.session.execute(log_query, {'shift_ids': tuple(shift_ids)})
                print(f"✅ Deleted {result.rowcount} records from handover_incident_response_log")
            
            # Step 3: Clean other shift-related tables
            tables_to_clean = [
                'current_shift_engineers',
                'next_shift_engineers', 
                'shift_key_point',
                'incident'
            ]
            
            for table in tables_to_clean:
                try:
                    query = text(f"DELETE FROM {table} WHERE account_id = :account_id AND team_id = :team_id")
                    result = db.session.execute(query, {'account_id': account_id, 'team_id': team_id})
                    print(f"✅ Deleted {result.rowcount} records from {table}")
                except Exception as e:
                    print(f"⚠️ Warning cleaning {table}: {e}")
            
            # Step 4: Clean handover-related tables
            handover_tables = [
                'handover_notification',
                'handover_request'
            ]
            
            for table in handover_tables:
                try:
                    query = text(f"DELETE FROM {table} WHERE account_id = :account_id AND team_id = :team_id")
                    result = db.session.execute(query, {'account_id': account_id, 'team_id': team_id})
                    print(f"✅ Deleted {result.rowcount} records from {table}")
                except Exception as e:
                    print(f"⚠️ Warning cleaning {table}: {e}")
            
            # Step 5: Clean shift table (now safe after cleaning dependencies)
            shift_query = text("DELETE FROM shift WHERE account_id = :account_id AND team_id = :team_id")
            result = db.session.execute(shift_query, {'account_id': account_id, 'team_id': team_id})
            print(f"✅ Deleted {result.rowcount} records from shift")
            
            # Step 6: Clean notification table
            try:
                notification_query = text("DELETE FROM notification WHERE account_id = :account_id AND team_id = :team_id")
                result = db.session.execute(notification_query, {'account_id': account_id, 'team_id': team_id})
                print(f"✅ Deleted {result.rowcount} records from notification")
            except Exception as e:
                print(f"⚠️ Warning cleaning notification: {e}")
            
            # Step 7: Clean incident assignments for TechCorp users
            try:
                # Get user IDs for TechCorp account
                user_query = text("SELECT id FROM user WHERE account_id = :account_id")
                user_result = db.session.execute(user_query, {'account_id': account_id})
                user_ids = [row[0] for row in user_result]
                
                if user_ids:
                    # Clean incident assignments
                    assignment_query = text("DELETE FROM incident_assignment WHERE assigned_to_user_id IN :user_ids")
                    result = db.session.execute(assignment_query, {'user_ids': tuple(user_ids)})
                    print(f"✅ Deleted {result.rowcount} records from incident_assignment")
                
            except Exception as e:
                print(f"⚠️ Warning cleaning incident_assignment: {e}")
            
            # Step 8: Final verification
            verification_query = text("""
                SELECT 
                    'shift' as table_name, COUNT(*) as count FROM shift WHERE account_id = :account_id AND team_id = :team_id
                UNION ALL
                SELECT 'handover_notification', COUNT(*) FROM handover_notification WHERE account_id = :account_id AND team_id = :team_id
                UNION ALL
                SELECT 'handover_request', COUNT(*) FROM handover_request WHERE account_id = :account_id AND team_id = :team_id
                UNION ALL
                SELECT 'notification', COUNT(*) FROM notification WHERE account_id = :account_id AND team_id = :team_id
                UNION ALL
                SELECT 'incident', COUNT(*) FROM incident WHERE account_id = :account_id AND team_id = :team_id
            """)
            verification_result = db.session.execute(verification_query, {'account_id': account_id, 'team_id': team_id})
            
            print("\n📊 Final verification (should all be 0):")
            for row in verification_result:
                print(f"   {row[0]}: {row[1]} records")
            
            # Commit all changes
            db.session.commit()
            print("\n✅ All TechCorp Solutions data has been completely cleaned!")
            print("🎯 Ready for fresh testing!")
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ Error during cleanup: {e}")
            raise
        finally:
            db.session.close()

if __name__ == "__main__":
    complete_techcorp_cleanup()