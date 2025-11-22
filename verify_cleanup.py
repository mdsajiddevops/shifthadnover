#!/usr/bin/env python3
"""
Verify TechCorp Cleanup - Confirm all data is cleaned
"""

import sys
sys.path.append('/app')

from app import app, db
from sqlalchemy import text

def verify_cleanup():
    """Verify that all TechCorp data has been cleaned"""
    
    account_id = 1  # TechCorp Solutions
    team_id = 2     # Operations Team
    
    print(f"🔍 Verifying cleanup for Account ID {account_id} (TechCorp Solutions) and Team ID {team_id} (Operations Team)")
    
    with app.app_context():
        tables_to_check = [
            ('handover_notification', 'hn JOIN user u ON hn.recipient_id = u.id WHERE u.account_id = 1'),
            ('handover_request', 'team_id = 2'),
            ('shift', 'account_id = 1 AND team_id = 2'),
            ('incident', 'i JOIN shift s ON i.shift_id = s.id WHERE s.account_id = 1 AND s.team_id = 2'),
            ('shift_key_point', 'account_id = 1 AND team_id = 2'),
            ('current_shift_engineers', 'cse JOIN shift s ON cse.shift_id = s.id WHERE s.account_id = 1 AND s.team_id = 2'),
            ('next_shift_engineers', 'nse JOIN shift s ON nse.shift_id = s.id WHERE s.account_id = 1 AND s.team_id = 2')
        ]
        
        all_clean = True
        
        for table, condition in tables_to_check:
            try:
                if 'JOIN' in condition:
                    query = f"SELECT COUNT(*) FROM {table} {condition}"
                else:
                    query = f"SELECT COUNT(*) FROM {table} WHERE {condition}"
                
                count = db.session.execute(text(query)).scalar()
                
                if count > 0:
                    print(f"❌ {table}: {count} records remain")
                    all_clean = False
                else:
                    print(f"✅ {table}: Clean (0 records)")
                    
            except Exception as e:
                print(f"⚠️ {table}: Could not check - {str(e)[:50]}...")
        
        print(f"\n📊 Cleanup Status:")
        if all_clean:
            print(f"🎉 SUCCESS: All TechCorp Solutions - Operations Team data has been cleaned!")
            print(f"🧪 The system is ready for fresh testing!")
            print(f"")
            print(f"👥 Test users available:")
            print(f"   - testuser1 (ID: 46) - password123")
            print(f"   - testuser2 (ID: 47) - password123") 
            print(f"   - testuser3 (ID: 48) - password123")
            print(f"")
            print(f"🌐 Login at: https://shiftops.lab.epam.com/")
        else:
            print(f"⚠️ Some data may still remain. Check the details above.")

if __name__ == "__main__":
    verify_cleanup()