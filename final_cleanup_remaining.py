#!/usr/bin/env python3

"""
Final targeted cleanup for remaining TechCorp data
"""

import sys
import os

# Change to app directory
os.chdir('/app')
sys.path.insert(0, '/app')

# Import the Flask app and database
from app import app, db
from sqlalchemy import text

def final_cleanup():
    """Final cleanup of remaining TechCorp data"""
    
    with app.app_context():
        account_id = 1  # TechCorp Solutions
        team_id = 2     # Operations Team
        
        print("🔧 Final cleanup of remaining TechCorp data:")
        
        try:
            # Clean remaining handover notifications
            query1 = text("DELETE FROM handover_notification WHERE account_id = :account_id AND team_id = :team_id")
            result1 = db.session.execute(query1, {'account_id': account_id, 'team_id': team_id})
            print(f"✅ Deleted {result1.rowcount} handover_notification records")
            
            # Clean remaining handover requests
            query2 = text("DELETE FROM handover_request WHERE account_id = :account_id AND team_id = :team_id")
            result2 = db.session.execute(query2, {'account_id': account_id, 'team_id': team_id})
            print(f"✅ Deleted {result2.rowcount} handover_request records")
            
            # Clean remaining shifts
            query3 = text("DELETE FROM shift WHERE account_id = :account_id AND team_id = :team_id")
            result3 = db.session.execute(query3, {'account_id': account_id, 'team_id': team_id})
            print(f"✅ Deleted {result3.rowcount} shift records")
            
            # Commit the changes
            db.session.commit()
            print("✅ Final cleanup committed successfully!")
            
            # Verify final state
            print("\n📊 Final verification:")
            tables = ['shift', 'handover_notification', 'handover_request', 'incident']
            for table in tables:
                query = text(f"SELECT COUNT(*) FROM {table} WHERE account_id = :account_id AND team_id = :team_id")
                result = db.session.execute(query, {'account_id': account_id, 'team_id': team_id})
                count = result.scalar()
                status = "✅ CLEAN" if count == 0 else f"⚠️ {count} records"
                print(f"   {table}: {status}")
            
            print("\n🎉 TechCorp Solutions data completely cleaned!")
            print("🚀 Ready for fresh handover testing!")
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ Error: {e}")
            raise
        finally:
            db.session.close()

if __name__ == "__main__":
    final_cleanup()