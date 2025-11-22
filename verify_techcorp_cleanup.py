#!/usr/bin/env python3

"""
Simple verification script to check cleanup results
"""

import sys
import os

# Change to app directory
os.chdir('/app')
sys.path.insert(0, '/app')

# Import the Flask app and database
from app import app, db
from sqlalchemy import text

def verify_cleanup():
    """Verify TechCorp Solutions data cleanup results"""
    
    with app.app_context():
        account_id = 1  # TechCorp Solutions
        team_id = 2     # Operations Team
        
        print("🔍 Verifying TechCorp Solutions cleanup results:")
        print("=" * 50)
        
        # Check main tables
        tables_to_check = [
            'shift',
            'handover_notification', 
            'handover_request',
            'incident'
        ]
        
        for table in tables_to_check:
            try:
                query = text(f"SELECT COUNT(*) FROM {table} WHERE account_id = :account_id AND team_id = :team_id")
                result = db.session.execute(query, {'account_id': account_id, 'team_id': team_id})
                count = result.scalar()
                status = "✅ CLEAN" if count == 0 else f"⚠️ {count} records remain"
                print(f"{table:25} : {status}")
            except Exception as e:
                print(f"{table:25} : ❌ Error checking: {str(e)[:50]}")
        
        # Check incident assignments for TechCorp users
        try:
            user_query = text("SELECT COUNT(*) FROM user WHERE account_id = :account_id")
            user_result = db.session.execute(user_query, {'account_id': account_id})
            user_count = user_result.scalar()
            print(f"{'TechCorp users':25} : {user_count} users remain (should be >0)")
        except Exception as e:
            print(f"{'TechCorp users':25} : ❌ Error: {str(e)[:50]}")
        
        print("=" * 50)
        print("✅ Cleanup verification complete!")
        print("🎯 Ready for fresh handover testing!")

if __name__ == "__main__":
    verify_cleanup()