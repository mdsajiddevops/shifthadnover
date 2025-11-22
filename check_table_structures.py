#!/usr/bin/env python3

"""
Check all table structures to understand the correct column names
"""

import sys
import os

# Change to app directory
os.chdir('/app')
sys.path.insert(0, '/app')

# Import the Flask app and database
from app import app, db
from sqlalchemy import text

def check_table_structures():
    """Check all relevant table structures"""
    
    with app.app_context():
        print("🔍 Checking table structures for correct column names")
        print("=" * 70)
        
        tables = [
            'handover_notification',
            'incident_assignment', 
            'handover_incident_response_log',
            'team_member',
            'user'
        ]
        
        for table in tables:
            print(f"\n📋 {table.upper()} TABLE:")
            try:
                columns_query = text(f"SHOW COLUMNS FROM {table}")
                columns = db.session.execute(columns_query).fetchall()
                for col in columns:
                    print(f"   {col[0]} ({col[1]})")
            except Exception as e:
                print(f"   ❌ Error: {e}")
        
        print("\n" + "=" * 70)
        print("🎯 Table structure check complete!")

if __name__ == "__main__":
    check_table_structures()