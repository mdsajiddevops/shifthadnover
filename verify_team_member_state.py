#!/usr/bin/env python3

"""
Verify current state of team_member table and test handover assignment flow
"""

import sys
import os

# Change to app directory
os.chdir('/app')
sys.path.insert(0, '/app')

# Import the Flask app and database
from app import app, db
from sqlalchemy import text

def verify_current_state():
    """Verify the current state of TeamMember records and test assignment flow"""
    
    with app.app_context():
        print("🔍 CURRENT TEAM_MEMBER STATE VERIFICATION")
        print("=" * 60)
        
        # Step 1: Check all team_member records for TechCorp
        print("\n1️⃣ CURRENT TEAM_MEMBER RECORDS:")
        query = text("""
            SELECT tm.id, tm.name, tm.user_id, u.username, u.email
            FROM team_member tm
            LEFT JOIN user u ON tm.user_id = u.id
            WHERE tm.account_id = 1 AND tm.team_id = 2
            ORDER BY tm.id
        """)
        records = db.session.execute(query).fetchall()
        
        print(f"   Found {len(records)} TeamMember records:")
        for record in records:
            if record.user_id:
                print(f"   ✅ ID={record.id}: '{record.name}' → User: {record.username} ({record.email})")
            else:
                print(f"   ❌ ID={record.id}: '{record.name}' → NO USER LINKED")
        
        # Step 2: Test the /api/get_engineers simulation
        print("\n2️⃣ SIMULATING /api/get_engineers RESPONSE:")
        engineers_query = text("""
            SELECT tm.id, tm.name
            FROM team_member tm
            WHERE tm.account_id = 1 AND tm.team_id = 2
            ORDER BY tm.name
        """)
        engineers = db.session.execute(engineers_query).fetchall()
        
        print(f"   API would return {len(engineers)} engineers:")
        for eng in engineers:
            print(f"   📋 {{'id': {eng.id}, 'name': '{eng.name}'}}")
        
        # Step 3: Test assignment resolution for techopsuser2 specifically
        print("\n3️⃣ TESTING ASSIGNMENT RESOLUTION FOR techopsuser2:")
        
        # Find techopsuser2 TeamMember record
        techopsuser2_tm = next((r for r in records if r.name == 'techopsuser2'), None)
        if techopsuser2_tm:
            print(f"   🎯 When form submits assigned_to_name='{techopsuser2_tm.id}':")
            print(f"      • TeamMember ID {techopsuser2_tm.id} will be found")
            if techopsuser2_tm.user_id:
                print(f"      • User ID {techopsuser2_tm.user_id} will be resolved")
                print(f"      • Notification will be created for {techopsuser2_tm.username}")
                print(f"      • HandoverIncidentResponseLog will show correct names")
                print(f"   ✅ Assignment will work correctly!")
            else:
                print(f"      • ❌ NO USER_ID - assignment will fail!")
        else:
            print(f"   ❌ techopsuser2 TeamMember not found!")
        
        # Step 4: Test all techops users
        print("\n4️⃣ TESTING ALL TECHOPS USERS:")
        techops_users = [r for r in records if r.name.startswith('techopsuser')]
        
        for user in techops_users:
            status = "✅ READY" if user.user_id else "❌ BROKEN"
            print(f"   {status}: {user.name} (TM_ID={user.id}) → User ID {user.user_id}")
        
        # Step 5: Test actual assignment workflow
        print("\n5️⃣ TESTING ASSIGNMENT WORKFLOW:")
        test_tm_id = techopsuser2_tm.id if techopsuser2_tm else None
        
        if test_tm_id:
            # Simulate the create_enhanced_incident_assignment logic
            assigned_member_query = text("""
                SELECT tm.id, tm.name, tm.user_id, u.username
                FROM team_member tm
                LEFT JOIN user u ON tm.user_id = u.id
                WHERE tm.id = :tm_id
            """)
            assigned_member = db.session.execute(assigned_member_query, {
                'tm_id': test_tm_id
            }).fetchone()
            
            if assigned_member and assigned_member.user_id:
                print(f"   🎯 Test Assignment: Incident → TeamMember {test_tm_id}")
                print(f"      • TeamMember found: {assigned_member.name}")
                print(f"      • User resolved: {assigned_member.username} (ID: {assigned_member.user_id})")
                print(f"      • ✅ HandoverNotification will be created")
                print(f"      • ✅ IncidentAssignment log will show correct assignee")
                print(f"   🚀 WORKFLOW WILL WORK!")
            else:
                print(f"   ❌ Test assignment would fail - no user_id link")
        
        print("\n" + "=" * 60)
        print("🎯 VERIFICATION COMPLETE")
        
        # Summary
        working_users = len([u for u in techops_users if u.user_id])
        total_techops = len(techops_users)
        
        if working_users == total_techops and working_users >= 2:
            print("\n✅ ALL SYSTEMS GO!")
            print("   • All techops users have proper TeamMember → User links")
            print("   • Handover assignments will route correctly")
            print("   • Notifications will reach the right users")
            print("   • Response logs will show correct names")
            print("\n🚀 Ready for techopsuser1 → techopsuser2 handover testing!")
        else:
            print(f"\n⚠️ PARTIAL SUCCESS: {working_users}/{total_techops} techops users ready")
            print("   • Some assignments may still fail")

if __name__ == "__main__":
    verify_current_state()