#!/usr/bin/env python3

"""
Comprehensive cleanup of orphaned team_member entries with all foreign key handling
"""

import sys
import os

# Change to app directory
os.chdir('/app')
sys.path.insert(0, '/app')

# Import the Flask app and database
from app import app, db
from sqlalchemy import text

def comprehensive_team_member_cleanup():
    """Comprehensively clean up orphaned team_member entries"""
    
    with app.app_context():
        print("🧹 Comprehensive cleanup of orphaned team_member entries")
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
        orphaned_ids = [record.id for record in orphaned]
        
        print(f"   Found {len(orphaned)} orphaned records:")
        for record in orphaned:
            print(f"      TM_ID={record.id}: '{record.name}'")
        
        if not orphaned_ids:
            print("   ✅ No orphaned records found!")
            return True
        
        # Step 2: Clean up all foreign key references
        print("\n2️⃣ CLEANING UP ALL FOREIGN KEY REFERENCES:")
        
        # Define tables and their foreign key columns
        tables_to_clean = {
            'shift_roster': 'team_member_id',
            'current_shift_engineers': 'team_member_id', 
            'next_shift_engineers': 'team_member_id',
            'shift_key_point': 'responsible_engineer_id'
        }
        
        total_deleted = 0
        
        for table, fk_column in tables_to_clean.items():
            try:
                # Check if references exist
                check_query = text(f"""
                    SELECT COUNT(*) FROM {table} 
                    WHERE {fk_column} IN :orphaned_ids
                """)
                count = db.session.execute(check_query, {
                    'orphaned_ids': tuple(orphaned_ids)
                }).scalar()
                
                if count > 0:
                    # Delete references
                    delete_query = text(f"""
                        DELETE FROM {table} 
                        WHERE {fk_column} IN :orphaned_ids
                    """)
                    result = db.session.execute(delete_query, {
                        'orphaned_ids': tuple(orphaned_ids)
                    })
                    deleted = result.rowcount
                    total_deleted += deleted
                    print(f"   ✅ {table}.{fk_column}: Deleted {deleted} references")
                else:
                    print(f"   ✅ {table}.{fk_column}: No references found")
                    
            except Exception as e:
                print(f"   ⚠️ {table}.{fk_column}: Error checking - {str(e)[:50]}...")
        
        print(f"   📊 Total foreign key references removed: {total_deleted}")
        
        # Step 3: Now safely delete orphaned team_member records
        print("\n3️⃣ DELETING ORPHANED TEAM_MEMBER RECORDS:")
        try:
            delete_query = text("""
                DELETE FROM team_member 
                WHERE account_id = 1 AND team_id = 2 AND user_id IS NULL
            """)
            result = db.session.execute(delete_query)
            deleted_count = result.rowcount
            
            db.session.commit()
            print(f"   ✅ Successfully deleted {deleted_count} orphaned team_member records")
            
        except Exception as e:
            db.session.rollback()
            print(f"   ❌ Error during deletion: {e}")
            return False
        
        # Step 4: Verify cleanup results
        print("\n4️⃣ VERIFICATION:")
        
        # Check for remaining duplicates
        verify_query = text("""
            SELECT 
                name,
                COUNT(*) as count,
                GROUP_CONCAT(DISTINCT id ORDER BY id) as tm_ids,
                GROUP_CONCAT(DISTINCT user_id ORDER BY user_id) as user_ids
            FROM team_member 
            WHERE account_id = 1 AND team_id = 2
            GROUP BY name
            ORDER BY name
        """)
        all_records = db.session.execute(verify_query).fetchall()
        
        duplicates = [r for r in all_records if r.count > 1]
        
        if duplicates:
            print("   ❌ Still have duplicates:")
            for dup in duplicates:
                print(f"      '{dup.name}': {dup.count} entries (IDs: {dup.tm_ids})")
        else:
            print("   ✅ No duplicates remaining!")
        
        # Check for orphaned records
        orphaned_check = text("""
            SELECT COUNT(*) FROM team_member 
            WHERE account_id = 1 AND team_id = 2 AND user_id IS NULL
        """)
        remaining_orphaned = db.session.execute(orphaned_check).scalar()
        
        if remaining_orphaned > 0:
            print(f"   ❌ Still have {remaining_orphaned} orphaned records")
        else:
            print("   ✅ No orphaned records remaining!")
        
        print(f"   📊 Total valid team_member records: {len(all_records)}")
        
        # Step 5: Show techops users specifically
        print("\n5️⃣ TECHOPS USERS STATUS:")
        techops_query = text("""
            SELECT tm.id, tm.name, tm.user_id, u.username, u.email
            FROM team_member tm
            LEFT JOIN user u ON tm.user_id = u.id
            WHERE tm.account_id = 1 AND tm.team_id = 2
            AND tm.name LIKE 'techopsuser%'
            ORDER BY tm.name
        """)
        techops_users = db.session.execute(techops_query).fetchall()
        
        print(f"   Found {len(techops_users)} techops users:")
        for user in techops_users:
            if user.user_id:
                print(f"   ✅ {user.name} (TM_ID={user.id}) → {user.username} ({user.email})")
            else:
                print(f"   ❌ {user.name} (TM_ID={user.id}) → NO USER LINKED")
        
        # Step 6: Final dropdown simulation
        print("\n6️⃣ FINAL DROPDOWN SIMULATION:")
        dropdown_query = text("""
            SELECT tm.id, tm.name, u.username
            FROM team_member tm
            JOIN user u ON tm.user_id = u.id
            WHERE tm.account_id = 1 AND tm.team_id = 2
            ORDER BY tm.name
        """)
        dropdown_items = db.session.execute(dropdown_query).fetchall()
        
        print(f"   📋 Dropdown will show {len(dropdown_items)} assignable users")
        
        # Count techops users in dropdown
        techops_in_dropdown = [item for item in dropdown_items if item.name.startswith('techopsuser')]
        print(f"   🎯 Techops users in dropdown: {len(techops_in_dropdown)}")
        for item in techops_in_dropdown:
            print(f"      ✅ ID={item.id}: {item.name} → {item.username}")
        
        print("\n" + "=" * 70)
        print("🎉 COMPREHENSIVE CLEANUP COMPLETE!")
        
        success = (len(duplicates) == 0 and remaining_orphaned == 0 and len(techops_in_dropdown) >= 2)
        
        if success:
            print("\n✅ PERFECT RESULTS:")
            print("   • All orphaned team_member records removed")
            print("   • All foreign key references cleaned")
            print("   • No duplicates remaining")
            print("   • All techops users properly mapped")
            print("   • Dropdown shows only assignable users")
            print("\n🚀 READY: techopsuser1 → techopsuser2 handover will work perfectly!")
        else:
            print("\n⚠️ PARTIAL SUCCESS - Some issues may remain")
        
        return success

if __name__ == "__main__":
    comprehensive_team_member_cleanup()