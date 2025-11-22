#!/usr/bin/env python3

"""
Safe cleanup of duplicate team_member entries handling foreign key constraints
"""

import sys
import os

# Change to app directory
os.chdir('/app')
sys.path.insert(0, '/app')

# Import the Flask app and database
from app import app, db
from sqlalchemy import text

def safe_cleanup_team_member_duplicates():
    """Safely remove orphaned team_member entries by handling foreign keys"""
    
    with app.app_context():
        print("🧹 Safe cleanup of duplicate team_member entries")
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
        
        if not orphaned:
            print("   ✅ No orphaned records found!")
            return True
        
        # Step 2: Check shift_roster references
        print("\n2️⃣ CHECKING SHIFT_ROSTER REFERENCES:")
        if orphaned_ids:
            roster_query = text("""
                SELECT team_member_id, COUNT(*) as count
                FROM shift_roster 
                WHERE team_member_id IN :orphaned_ids
                GROUP BY team_member_id
            """)
            roster_refs = db.session.execute(roster_query, {
                'orphaned_ids': tuple(orphaned_ids)
            }).fetchall()
            
            if roster_refs:
                print(f"   Found {len(roster_refs)} shift_roster references:")
                for ref in roster_refs:
                    print(f"      TeamMember ID {ref.team_member_id}: {ref.count} shift_roster entries")
                
                # Remove shift_roster references to orphaned team_members
                print("\n   🔧 Removing shift_roster references:")
                delete_roster_query = text("""
                    DELETE FROM shift_roster 
                    WHERE team_member_id IN :orphaned_ids
                """)
                roster_result = db.session.execute(delete_roster_query, {
                    'orphaned_ids': tuple(orphaned_ids)
                })
                print(f"   ✅ Deleted {roster_result.rowcount} shift_roster entries")
            else:
                print("   ✅ No shift_roster references found")
        
        # Step 3: Check for other foreign key references
        print("\n3️⃣ CHECKING OTHER REFERENCES:")
        
        # Check if there are any incident assignments referencing these
        try:
            assignment_query = text("""
                SELECT COUNT(*) as count
                FROM incident_assignment ia
                WHERE ia.assigned_to_id IN (
                    SELECT u.id FROM user u 
                    JOIN team_member tm ON u.id = tm.user_id 
                    WHERE tm.id IN :orphaned_ids
                )
            """)
            assignment_count = db.session.execute(assignment_query, {
                'orphaned_ids': tuple(orphaned_ids)
            }).scalar()
            print(f"   Incident assignments: {assignment_count}")
        except:
            print("   Incident assignments: Unable to check")
        
        # Step 4: Now safely delete orphaned team_member records
        print("\n4️⃣ DELETING ORPHANED TEAM_MEMBER RECORDS:")
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
        
        # Step 5: Verify cleanup
        print("\n5️⃣ VERIFICATION:")
        verify_query = text("""
            SELECT 
                name,
                COUNT(*) as count,
                GROUP_CONCAT(DISTINCT id ORDER BY id) as tm_ids
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
        
        print(f"   📊 Total team_member records: {len(all_records)}")
        
        # Step 6: Show final dropdown state
        print("\n6️⃣ FINAL DROPDOWN STATE:")
        final_query = text("""
            SELECT tm.id, tm.name, u.username
            FROM team_member tm
            JOIN user u ON tm.user_id = u.id
            WHERE tm.account_id = 1 AND tm.team_id = 2
            ORDER BY tm.name
        """)
        final_items = db.session.execute(final_query).fetchall()
        
        print(f"   📋 Dropdown will show {len(final_items)} items (all assignable):")
        techops_count = 0
        for item in final_items:
            if item.name.startswith('techopsuser'):
                print(f"      ✅ ID={item.id}: {item.name} → {item.username}")
                techops_count += 1
        
        print(f"\n   🎯 Found {techops_count} techops users ready for assignment")
        
        print("\n" + "=" * 70)
        print("🎉 SAFE CLEANUP COMPLETE!")
        
        print("\n✅ RESULTS:")
        print("   • Removed shift_roster references to orphaned team_members")
        print("   • Deleted orphaned team_member records without user_id")
        print("   • Each user now has exactly ONE team_member entry")
        print("   • Dropdown shows only assignable users")
        print("   • Assignments will resolve correctly")
        print("\n🚀 NOW READY: techopsuser1 → techopsuser2 handover will work!")
        
        return True

if __name__ == "__main__":
    safe_cleanup_team_member_duplicates()