#!/usr/bin/env python3

"""
Test the complete handover flow after TeamMember fixes
"""

import sys
import os

# Change to app directory
os.chdir('/app')
sys.path.insert(0, '/app')

# Import the Flask app and database
from app import app, db
from sqlalchemy import text

def test_handover_flow():
    """Test the complete handover flow with correct column names"""
    
    with app.app_context():
        print("🧪 Testing complete handover flow after TeamMember fixes")
        print("=" * 70)
        
        # Step 1: Verify TeamMember records are active
        print("\n1️⃣ TEAMMEMBER VERIFICATION:")
        tm_query = text("""
            SELECT 
                u.id, u.username, u.email,
                tm.id as tm_id, tm.name, tm.role, tm.is_active
            FROM user u
            JOIN team_member tm ON u.id = tm.user_id
            WHERE u.username IN ('testuser1', 'testuser2')
            ORDER BY u.username
        """)
        team_members = db.session.execute(tm_query).fetchall()
        
        for tm in team_members:
            status = "✅ ACTIVE" if tm.is_active else "❌ INACTIVE"
            print(f"   {tm.username}: TM_ID={tm.tm_id}, Role={tm.role}, Status={status}")
        
        # Step 2: Check recent handover requests with correct columns
        print("\n2️⃣ RECENT HANDOVER REQUESTS:")
        hr_query = text("""
            SELECT 
                hr.id, hr.created_by_id, hr.shift_date, hr.status,
                hr.current_shift_type, hr.next_shift_type, hr.created_at,
                u.username as created_by_username
            FROM handover_request hr
            JOIN user u ON hr.created_by_id = u.id
            WHERE hr.account_id = 1 AND hr.team_id = 2
            ORDER BY hr.created_at DESC
            LIMIT 3
        """)
        handovers = db.session.execute(hr_query).fetchall()
        
        if handovers:
            for hr in handovers:
                print(f"   Handover ID={hr.id}: {hr.created_by_username}")
                print(f"      Date: {hr.shift_date}, Status: {hr.status}")
                print(f"      Shift: {hr.current_shift_type} → {hr.next_shift_type}")
                print(f"      Created: {hr.created_at}")
                print()
        else:
            print("   ℹ️ No handover requests found")
        
        # Step 3: Check handover notifications with correct columns
        print("3️⃣ HANDOVER NOTIFICATIONS:")
        hn_query = text("""
            SELECT 
                hn.id, hn.recipient_id, hn.notification_type,
                hn.title, hn.is_read, hn.created_at,
                u.username as recipient_username
            FROM handover_notification hn
            JOIN user u ON hn.recipient_id = u.id
            WHERE hn.account_id = 1 AND hn.team_id = 2
            ORDER BY hn.created_at DESC
            LIMIT 5
        """)
        notifications = db.session.execute(hn_query).fetchall()
        
        if notifications:
            for hn in notifications:
                read_status = "✅ READ" if hn.is_read else "📬 UNREAD"
                print(f"   Notification ID={hn.id}: {hn.notification_type}")
                print(f"      To: {hn.recipient_username}, Status: {read_status}")
                print(f"      Title: {hn.title}")
                print(f"      Created: {hn.created_at}")
                print()
        else:
            print("   ℹ️ No notifications found")
        
        # Step 4: Check incident assignments with correct columns
        print("4️⃣ INCIDENT ASSIGNMENTS:")
        ia_query = text("""
            SELECT 
                ia.id, ia.incident_title, ia.assigned_to_id, ia.assigned_by_id,
                ia.assignment_status, ia.incident_status, ia.created_at,
                u1.username as assigned_to_username,
                u2.username as assigned_by_username
            FROM incident_assignment ia
            JOIN user u1 ON ia.assigned_to_id = u1.id
            JOIN user u2 ON ia.assigned_by_id = u2.id
            WHERE ia.account_id = 1 AND ia.team_id = 2
            ORDER BY ia.created_at DESC
            LIMIT 5
        """)
        assignments = db.session.execute(ia_query).fetchall()
        
        if assignments:
            for ia in assignments:
                print(f"   Assignment ID={ia.id}: {ia.incident_title}")
                print(f"      From: {ia.assigned_by_username} → To: {ia.assigned_to_username}")
                print(f"      Status: {ia.assignment_status}, Incident: {ia.incident_status}")
                print(f"      Created: {ia.created_at}")
                print()
        else:
            print("   ℹ️ No incident assignments found")
        
        # Step 5: Check incident response logs with correct columns
        print("5️⃣ INCIDENT RESPONSE LOGS:")
        irl_query = text("""
            SELECT 
                irl.id, irl.incident_title, irl.assigned_by_name, 
                irl.assigned_by_email, irl.accepted_by_name, irl.accepted_by_email,
                irl.response_status, irl.created_at
            FROM handover_incident_response_log irl
            WHERE irl.account_id = 1 AND irl.team_id = 2
            ORDER BY irl.created_at DESC
            LIMIT 5
        """)
        response_logs = db.session.execute(irl_query).fetchall()
        
        if response_logs:
            for irl in response_logs:
                print(f"   Response Log ID={irl.id}: {irl.incident_title}")
                print(f"      Assigned by: {irl.assigned_by_name} ({irl.assigned_by_email})")
                print(f"      Accepted by: {irl.accepted_by_name} ({irl.accepted_by_email})")
                print(f"      Status: {irl.response_status}")
                print(f"      Created: {irl.created_at}")
                print()
        else:
            print("   ℹ️ No response logs found")
        
        print("=" * 70)
        print("🎯 Handover flow test complete!")
        
        # Analyze the situation
        print("\n📊 ANALYSIS:")
        if not handovers:
            print("   🚨 CRITICAL: No handover requests found!")
            print("   → User needs to submit a NEW handover for testing")
        elif not notifications:
            print("   🚨 ISSUE: Handovers exist but no notifications generated")
            print("   → Notification creation may be failing")
        elif not assignments:
            print("   🚨 ISSUE: Notifications exist but no incident assignments")
            print("   → Incident assignment creation may be failing")
        else:
            print("   ✅ Data flow appears to be working")
            print("   → Check if testuser2 sees notifications on dashboard")
        
        print("\n🎯 NEXT ACTION:")
        print("   Please submit a NEW handover as testuser1 → testuser2")
        print("   Then check testuser2's dashboard for notifications")

if __name__ == "__main__":
    test_handover_flow()