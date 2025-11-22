#!/usr/bin/env python3

"""
Check for duplicate team_member entries and analyze dropdown/assignment issues
"""

import sys
import os

# Change to app directory
os.chdir('/app')
sys.path.insert(0, '/app')

# Import the Flask app and database
from app import app, db
from sqlalchemy import text

def analyze_team_member_duplicates():
    """Analyze team_member table for duplicates and their impact"""
    
    with app.app_context():
        print("🔍 Analyzing team_member table duplicates and dropdown impact")
        print("=" * 80)
        
        # Step 1: Check for duplicate entries by name in TechCorp Solutions
        print("\n1️⃣ CHECKING FOR DUPLICATE TEAM_MEMBER ENTRIES:")
        duplicate_query = text("""
            SELECT 
                name,
                COUNT(*) as count,
                GROUP_CONCAT(DISTINCT id ORDER BY id) as tm_ids,
                GROUP_CONCAT(DISTINCT user_id ORDER BY user_id) as user_ids,
                GROUP_CONCAT(DISTINCT CASE WHEN user_id IS NULL THEN 'NULL' ELSE CAST(user_id AS CHAR) END ORDER BY id) as user_id_details
            FROM team_member 
            WHERE account_id = 1 AND team_id = 2
            GROUP BY name
            HAVING COUNT(*) > 1
            ORDER BY name
        """)
        duplicates = db.session.execute(duplicate_query).fetchall()
        
        if duplicates:
            print("   ❌ FOUND DUPLICATE ENTRIES:")
            for dup in duplicates:
                print(f"   Name: '{dup.name}' - {dup.count} entries")
                print(f"      TeamMember IDs: {dup.tm_ids}")
                print(f"      User IDs: {dup.user_id_details}")
                print()
        else:
            print("   ✅ No duplicate names found")
        
        # Step 2: Check all team_member entries for TechCorp Solutions
        print("2️⃣ ALL TEAM_MEMBER ENTRIES (Account=1, Team=2):")
        all_tm_query = text("""
            SELECT 
                tm.id, tm.name, tm.user_id, tm.email as tm_email,
                u.username, u.email as user_email, u.is_active
            FROM team_member tm
            LEFT JOIN user u ON tm.user_id = u.id
            WHERE tm.account_id = 1 AND tm.team_id = 2
            ORDER BY tm.name, tm.id
        """)
        all_tms = db.session.execute(all_tm_query).fetchall()
        
        linked_count = 0
        unlinked_count = 0
        
        for tm in all_tms:
            if tm.user_id:
                status = f"✅ LINKED → User: {tm.username} ({tm.user_email}) Active: {tm.is_active}"
                linked_count += 1
            else:
                status = "❌ NO USER_ID - ORPHANED RECORD"
                unlinked_count += 1
            
            print(f"   TM_ID={tm.id}: '{tm.name}' {status}")
        
        print(f"\n   📊 SUMMARY: {linked_count} linked, {unlinked_count} unlinked")
        
        # Step 3: Simulate what /api/get_engineers returns
        print("\n3️⃣ WHAT /api/get_engineers DROPDOWN SHOWS:")
        engineers_query = text("""
            SELECT tm.id, tm.name, tm.user_id
            FROM team_member tm
            WHERE tm.account_id = 1 AND tm.team_id = 2
            ORDER BY tm.name
        """)
        engineers = db.session.execute(engineers_query).fetchall()
        
        dropdown_items = []
        problematic_items = []
        
        for eng in engineers:
            dropdown_items.append({'id': eng.id, 'name': eng.name})
            if not eng.user_id:
                problematic_items.append({'id': eng.id, 'name': eng.name})
        
        print(f"   📋 Dropdown will show {len(dropdown_items)} items:")
        for item in dropdown_items:
            has_user = "✅" if item['id'] not in [p['id'] for p in problematic_items] else "❌ NO USER"
            print(f"      ID={item['id']}: {item['name']} {has_user}")
        
        if problematic_items:
            print(f"\n   ⚠️ PROBLEMATIC: {len(problematic_items)} items without user_id:")
            for prob in problematic_items:
                print(f"      ID={prob['id']}: {prob['name']} - Assignment will FAIL")
        
        # Step 4: Test assignment resolution for problematic entries
        print("\n4️⃣ TESTING ASSIGNMENT RESOLUTION:")
        if problematic_items:
            test_item = problematic_items[0]
            print(f"   Testing assignment to TM_ID={test_item['id']} ('{test_item['name']}')")
            
            # Simulate create_enhanced_incident_assignment logic
            assigned_to_name = str(test_item['id'])
            if assigned_to_name.isdigit():
                team_member_id = int(assigned_to_name)
                team_id = 2
                
                resolve_query = text("""
                    SELECT tm.*, u.username
                    FROM team_member tm
                    LEFT JOIN user u ON tm.user_id = u.id
                    WHERE tm.id = :tm_id AND tm.team_id = :team_id
                """)
                resolved = db.session.execute(resolve_query, {
                    'tm_id': team_member_id, 
                    'team_id': team_id
                }).fetchone()
                
                if resolved:
                    if resolved.user_id:
                        print(f"   ✅ Would resolve to User ID {resolved.user_id} ({resolved.username})")
                    else:
                        print(f"   ❌ FOUND TeamMember but NO user_id - Assignment will FAIL")
                        print(f"   ❌ This causes fallback to hardcoded users like sachin_vakhare@epam.com")
                else:
                    print(f"   ❌ TeamMember not found - Assignment will FAIL")
        
        # Step 5: Check for specific techopsuser duplicates
        print("\n5️⃣ CHECKING TECHOPS USER DUPLICATES:")
        techops_names = ['techopsuser1', 'techopsuser2', 'techopsuser3', 'techopsuser4']
        
        for name in techops_names:
            name_query = text("""
                SELECT tm.id, tm.name, tm.user_id, u.username
                FROM team_member tm
                LEFT JOIN user u ON tm.user_id = u.id
                WHERE tm.name = :name AND tm.account_id = 1 AND tm.team_id = 2
                ORDER BY tm.id
            """)
            name_results = db.session.execute(name_query, {'name': name}).fetchall()
            
            if len(name_results) > 1:
                print(f"   ⚠️ {name}: {len(name_results)} entries")
                for res in name_results:
                    user_info = f"→ {res.username}" if res.user_id else "→ NO USER"
                    print(f"      TM_ID={res.id} {user_info}")
            elif len(name_results) == 1:
                res = name_results[0]
                user_info = f"→ {res.username}" if res.user_id else "→ NO USER"
                print(f"   ✅ {name}: 1 entry TM_ID={res.id} {user_info}")
            else:
                print(f"   ❌ {name}: Not found")
        
        print("\n" + "=" * 80)
        print("🎯 ANALYSIS COMPLETE!")
        
        # Step 6: Recommendations
        print("\n📋 RECOMMENDATIONS:")
        if duplicates or problematic_items:
            print("❌ ISSUES FOUND - ACTION REQUIRED:")
            print("   1. Clean up duplicate team_member entries")
            print("   2. Ensure all team_member records have valid user_id")
            print("   3. Remove orphaned records without user_id")
            print("\n🔧 PROPOSED FIX:")
            print("   - Keep team_member records WITH user_id")
            print("   - Delete team_member records WITHOUT user_id")
            print("   - This will ensure dropdown only shows assignable users")
        else:
            print("✅ NO ISSUES FOUND - System ready for testing!")
        
        return len(duplicates) > 0 or len(problematic_items) > 0

if __name__ == "__main__":
    analyze_team_member_duplicates()