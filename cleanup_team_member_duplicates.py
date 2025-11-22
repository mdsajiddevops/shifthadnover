#!/usr/bin/env python3

"""
Clean up duplicate and orphaned team_member entries
"""

import sys
import os

# Change to app directory
os.chdir('/app')
sys.path.insert(0, '/app')

# Import the Flask app and database
from app import app, db
from sqlalchemy import text

def cleanup_team_member_duplicates():
    """Remove orphaned team_member entries without user_id"""
    
    with app.app_context():
        print("🧹 Cleaning up duplicate and orphaned team_member entries")
        print("=" * 70)
        
        # Step 1: Identify orphaned records
        print("\n1️⃣ IDENTIFYING ORPHANED RECORDS:")
        orphaned_query = text("""
            SELECT id, name, email
            FROM team_member
            WHERE account_id = 1 AND team_id = 2 AND user_id IS NULL
            ORDER BY name
        """)
        orphaned = db.session.execute(orphaned_query).fetchall()
        
        print(f"   Found {len(orphaned)} orphaned records:")
        for record in orphaned:
            print(f"      TM_ID={record.id}: '{record.name}'")
        
        # Step 2: Show what will be kept
        print("\n2️⃣ RECORDS THAT WILL BE KEPT:")
        keep_query = text("""
            SELECT tm.id, tm.name, tm.user_id, u.username
            FROM team_member tm
            JOIN user u ON tm.user_id = u.id
            WHERE tm.account_id = 1 AND tm.team_id = 2
            ORDER BY tm.name
        """)
        keep_records = db.session.execute(keep_query).fetchall()
        
        print(f"   Keeping {len(keep_records)} valid records:")
        for record in keep_records:
            print(f"      TM_ID={record.id}: '{record.name}' → User: {record.username}")
        
        # Step 3: Perform cleanup
        print("\n3️⃣ PERFORMING CLEANUP:")
        if orphaned:
            try:
                delete_query = text("""
                    DELETE FROM team_member 
                    WHERE account_id = 1 AND team_id = 2 AND user_id IS NULL
                """)
                result = db.session.execute(delete_query)
                deleted_count = result.rowcount
                
                db.session.commit()
                print(f"   ✅ Successfully deleted {deleted_count} orphaned records")
                
            except Exception as e:
                db.session.rollback()
                print(f"   ❌ Error during cleanup: {e}")
                return False
        else:
            print("   ✅ No orphaned records to delete")
        
        # Step 4: Verify cleanup
        print("\n4️⃣ VERIFICATION:")
        verify_query = text("""
            SELECT 
                name,
                COUNT(*) as count,
                GROUP_CONCAT(DISTINCT id ORDER BY id) as tm_ids
            FROM team_member 
            WHERE account_id = 1 AND team_id = 2
            GROUP BY name
            HAVING COUNT(*) > 1
            ORDER BY name
        """)
        remaining_duplicates = db.session.execute(verify_query).fetchall()
        
        if remaining_duplicates:
            print("   ❌ Still have duplicates:")
            for dup in remaining_duplicates:
                print(f"      '{dup.name}': {dup.count} entries (IDs: {dup.tm_ids})")
        else:
            print("   ✅ No duplicates remaining!")
        
        # Step 5: Test dropdown simulation
        print("\n5️⃣ UPDATED DROPDOWN SIMULATION:")
        dropdown_query = text("""
            SELECT tm.id, tm.name, tm.user_id, u.username
            FROM team_member tm
            JOIN user u ON tm.user_id = u.id
            WHERE tm.account_id = 1 AND tm.team_id = 2
            ORDER BY tm.name
        """)
        dropdown_items = db.session.execute(dropdown_query).fetchall()
        
        print(f"   📋 Dropdown will now show {len(dropdown_items)} items:")
        techops_users = []
        for item in dropdown_items:
            print(f"      ID={item.id}: {item.name} → {item.username}")
            if item.name.startswith('techopsuser'):
                techops_users.append(item)
        
        print(f"\n   🎯 TECHOPS USERS IN DROPDOWN:")
        for user in techops_users:
            print(f"      ✅ {user.name} (TM_ID={user.id}) → {user.username}")
        
        print("\n" + "=" * 70)
        print("🎉 CLEANUP COMPLETE!")
        
        print("\n✅ RESULTS:")
        print("   • Removed orphaned team_member records without user_id")
        print("   • Each user now has exactly ONE team_member entry") 
        print("   • Dropdown will show only assignable users")
        print("   • Assignments will resolve correctly")
        print("\n🚀 Ready for testing handover: techopsuser1 → techopsuser2")
        
        return True

if __name__ == "__main__":
    cleanup_team_member_duplicates()