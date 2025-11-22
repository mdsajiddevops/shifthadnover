#!/usr/bin/env python3

"""
Debug TeamMember ID resolution for testuser1 and testuser2
"""

import sys
import os

# Change to app directory
os.chdir('/app')
sys.path.insert(0, '/app')

# Import the Flask app and database
from app import app, db
from sqlalchemy import text

def debug_team_member_resolution():
    """Debug how TeamMember IDs resolve to users"""
    
    with app.app_context():
        print("🔍 Debugging TeamMember ID resolution")
        print("=" * 70)
        
        # Step 1: Check testuser1 and testuser2 TeamMember records
        print("\n1️⃣ TESTUSER TEAMMEMBER RECORDS:")
        user_tm_query = text("""
            SELECT 
                u.id as user_id, u.username, u.email,
                tm.id as tm_id, tm.name as tm_name, tm.email as tm_email, tm.user_id as tm_user_id
            FROM user u
            JOIN team_member tm ON u.id = tm.user_id
            WHERE u.username IN ('testuser1', 'testuser2')
            ORDER BY u.username
        """)
        user_tms = db.session.execute(user_tm_query).fetchall()
        
        for utm in user_tms:
            print(f"   User: {utm.username} (ID={utm.user_id}), Email: {utm.email}")
            print(f"   TeamMember: ID={utm.tm_id}, Name={utm.tm_name}, Email={utm.tm_email}, Links to User ID={utm.tm_user_id}")
            print()
        
        # Step 2: Check what the /api/get_engineers endpoint would return
        print("2️⃣ SIMULATE /api/get_engineers RESPONSE:")
        tm_query = text("""
            SELECT 
                tm.id, tm.name, tm.email, tm.user_id,
                u.username, u.email as user_email
            FROM team_member tm
            LEFT JOIN user u ON tm.user_id = u.id
            WHERE tm.account_id = 1 AND tm.team_id = 2
            ORDER BY tm.id
        """)
        all_tms = db.session.execute(tm_query).fetchall()
        
        engineers_list = []
        for tm in all_tms:
            engineers_list.append({'id': tm.id, 'name': tm.name})
            user_link = f"→ User: {tm.username} ({tm.user_email})" if tm.username else "→ NO USER LINKED"
            print(f"   Engineers API would return: ID={tm.id}, Name={tm.name} {user_link}")
        
        print(f"\n   API Response: {engineers_list}")
        
        # Step 3: Test assignment resolution logic
        print("\n3️⃣ TESTING ASSIGNMENT RESOLUTION LOGIC:")
        
        # Test with testuser2's TeamMember ID
        testuser2_tm = next((tm for tm in all_tms if tm.username == 'testuser2'), None)
        if testuser2_tm:
            print(f"   Testing assignment to TeamMember ID {testuser2_tm.id} (should be testuser2)")
            
            # Simulate the logic from create_enhanced_incident_assignment
            assigned_to_name = str(testuser2_tm.id)  # This is what comes from the form
            
            if assigned_to_name.isdigit():
                team_member_id = int(assigned_to_name)
                team_id = 2  # Operations Team
                
                # Find team member by team member ID
                test_query = text("SELECT * FROM team_member WHERE id = :tm_id AND team_id = :team_id")
                result = db.session.execute(test_query, {'tm_id': team_member_id, 'team_id': team_id}).fetchone()
                
                if result:
                    print(f"   ✅ Found TeamMember: ID={result.id}, Name={result.name}, User ID={result.user_id}")
                    
                    if result.user_id:
                        user_query = text("SELECT * FROM user WHERE id = :user_id")
                        user_result = db.session.execute(user_query, {'user_id': result.user_id}).fetchone()
                        if user_result:
                            print(f"   ✅ Resolves to User: {user_result.username} ({user_result.email})")
                        else:
                            print(f"   ❌ No user found for User ID {result.user_id}")
                    else:
                        print(f"   ❌ TeamMember has no user_id")
                else:
                    print(f"   ❌ No TeamMember found for ID {team_member_id} in team {team_id}")
        
        # Step 4: Check if there are any assignments using wrong IDs
        print("\n4️⃣ CHECKING PROBLEMATIC ASSIGNMENTS:")
        
        # Look for any assignments that might be using incorrect user resolution
        problem_query = text("""
            SELECT 
                'response_log' as source,
                hirl.id, hirl.incident_title, 
                hirl.assigned_by_email, hirl.accepted_by_email
            FROM handover_incident_response_log hirl
            WHERE hirl.account_id = 1 AND hirl.team_id = 2
            AND (hirl.assigned_by_email LIKE '%sachin%' OR hirl.accepted_by_email LIKE '%sachin%')
            ORDER BY hirl.created_at DESC
            LIMIT 5
        """)
        
        problems = db.session.execute(problem_query).fetchall()
        if problems:
            for p in problems:
                print(f"   ❌ {p.source} ID={p.id}: {p.incident_title}")
                print(f"      Assigned by: {p.assigned_by_email}")
                print(f"      Accepted by: {p.accepted_by_email}")
                print()
        else:
            print("   ✅ No problematic assignments found")
        
        print("=" * 70)
        print("🎯 Debug complete!")
        
        # Step 5: Show the resolution path summary
        print("\n📋 RESOLUTION PATH SUMMARY:")
        print("   1. Frontend calls /api/get_engineers")
        print("   2. API returns TeamMember records: [{'id': tm.id, 'name': tm.name}, ...]")
        print("   3. Form submits with selected TeamMember ID (e.g., '55')")
        print("   4. create_enhanced_incident_assignment gets assigned_to_name='55'")
        print("   5. Function looks up TeamMember ID=55 in team_id=2")
        print("   6. Should find TeamMember record and get user_id")
        print("   7. Should create assignment with correct user_id")
        print()
        print("🔍 If assignments still go to sachin_vakhare@epam.com, the issue is:")
        print("   - Wrong TeamMember ID being passed from frontend")
        print("   - TeamMember lookup failing")
        print("   - User ID resolution failing")
        print("   - Hard-coded fallback to sachin_vakhare@epam.com somewhere")

if __name__ == "__main__":
    debug_team_member_resolution()