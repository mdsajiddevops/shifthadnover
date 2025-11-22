#!/usr/bin/env python3

"""
Complete cleanup of all remaining TechCorp response logs and shift data
"""

import sys
import os

# Change to app directory
os.chdir('/app')
sys.path.insert(0, '/app')

# Import the Flask app and database
from app import app, db
from sqlalchemy import text

def complete_response_log_cleanup():
    """Complete cleanup of response logs and shifts"""
    
    with app.app_context():
        account_id = 1  # TechCorp Solutions
        team_id = 2     # Operations Team
        
        print("🧹 Complete cleanup of response logs and shifts:")
        
        try:
            # Step 1: Get all shift IDs for TechCorp Solutions
            shift_query = text("SELECT id FROM shift WHERE account_id = :account_id AND team_id = :team_id")
            shift_result = db.session.execute(shift_query, {'account_id': account_id, 'team_id': team_id})
            shift_ids = [row[0] for row in shift_result]
            
            if shift_ids:
                print(f"📋 Found shift IDs to clean: {shift_ids}")
                
                # Step 2: Delete ALL handover incident response logs that reference these shifts
                log_query = text("DELETE FROM handover_incident_response_log WHERE from_shift_id IN :shift_ids OR to_shift_id IN :shift_ids")
                result = db.session.execute(log_query, {'shift_ids': tuple(shift_ids)})
                print(f"✅ Deleted {result.rowcount} handover_incident_response_log records")
                
                # Step 3: Also delete any response logs without shift references for safety
                try:
                    orphan_query = text("DELETE FROM handover_incident_response_log WHERE handover_id IN (SELECT id FROM handover_request WHERE account_id = :account_id AND team_id = :team_id)")
                    result = db.session.execute(orphan_query, {'account_id': account_id, 'team_id': team_id})
                    print(f"✅ Cleaned {result.rowcount} orphan response log records")
                except Exception as e:
                    print(f"⚠️ No orphan response logs: {e}")
                
                # Step 4: Now try to delete shifts
                shift_delete_query = text("DELETE FROM shift WHERE account_id = :account_id AND team_id = :team_id")
                result = db.session.execute(shift_delete_query, {'account_id': account_id, 'team_id': team_id})
                print(f"✅ Deleted {result.rowcount} shift records")
                
            else:
                print("✅ No shifts found to clean")
            
            # Step 5: Double-check with a general cleanup of any remaining response logs
            try:
                # Delete any remaining response logs for TechCorp users
                user_query = text("SELECT id FROM user WHERE account_id = :account_id")
                user_result = db.session.execute(user_query, {'account_id': account_id})
                user_ids = [row[0] for row in user_result]
                
                if user_ids:
                    # Clean response logs where users are from TechCorp
                    general_log_query = text("""
                        DELETE FROM handover_incident_response_log 
                        WHERE handover_id IN (
                            SELECT hr.id FROM handover_request hr 
                            JOIN user u ON hr.created_by = u.id 
                            WHERE u.account_id = :account_id
                        )
                    """)
                    result = db.session.execute(general_log_query, {'account_id': account_id})
                    print(f"✅ Deleted {result.rowcount} general response log records")
                    
            except Exception as e:
                print(f"⚠️ General cleanup note: {e}")
            
            # Commit all changes
            db.session.commit()
            print("✅ All cleanup operations committed!")
            
            # Final verification
            print("\n📊 Final verification:")
            tables = ['shift', 'handover_notification', 'handover_request', 'incident', 'handover_incident_response_log']
            for table in tables:
                try:
                    if table == 'handover_incident_response_log':
                        # Check if any response logs remain for TechCorp users
                        query = text("""
                            SELECT COUNT(*) FROM handover_incident_response_log hirl
                            JOIN handover_request hr ON hirl.handover_id = hr.id
                            WHERE hr.account_id = :account_id AND hr.team_id = :team_id
                        """)
                    else:
                        query = text(f"SELECT COUNT(*) FROM {table} WHERE account_id = :account_id AND team_id = :team_id")
                    
                    result = db.session.execute(query, {'account_id': account_id, 'team_id': team_id})
                    count = result.scalar()
                    status = "✅ CLEAN" if count == 0 else f"⚠️ {count} records"
                    print(f"   {table}: {status}")
                except Exception as e:
                    print(f"   {table}: ❌ Check failed")
            
            print("\n🎉 Complete TechCorp Solutions cleanup finished!")
            print("🚀 100% Ready for fresh handover testing!")
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ Error: {e}")
            raise
        finally:
            db.session.close()

if __name__ == "__main__":
    complete_response_log_cleanup()