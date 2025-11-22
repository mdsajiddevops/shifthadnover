#!/usr/bin/env python3

"""
Fix TeamMember records with correct field names and check handover flow
"""

import sys
import os

# Change to app directory
os.chdir('/app')
sys.path.insert(0, '/app')

# Import the Flask app and database
from app import app, db
from sqlalchemy import text

def fix_team_members_and_check_flow():
    """Fix TeamMember records and check handover flow"""
    
    with app.app_context():
        print("🔧 Fixing TeamMember records and checking handover flow")
        print("=" * 60)
        
        # Step 1: Get user details
        print("\n1️⃣ GETTING USER DETAILS:")
        user_query = text("""
            SELECT 
                u.id, u.username, u.email, u.account_id, u.team_id,
                tm.id as team_member_id
            FROM user u
            LEFT JOIN team_member tm ON u.id = tm.user_id
            WHERE u.username IN ('testuser1', 'testuser2')
            ORDER BY u.username
        """)
        users = db.session.execute(user_query).fetchall()
        
        for user in users:
            tm_status = "✅ EXISTS" if user.team_member_id else "❌ MISSING"
            print(f"   {user.username}: ID={user.id}, Email={user.email}, TeamMember={tm_status}")
        
        # Step 2: Create missing TeamMember records with all required fields
        print("\n2️⃣ CREATING TEAMMEMBER RECORDS:")
        try:
            for user in users:
                if not user.team_member_id:
                    # Create TeamMember record with all required fields
                    insert_query = text("""
                        INSERT INTO team_member (
                            user_id, name, email, contact_number, role, 
                            account_id, team_id, is_active, created_at, updated_at
                        )
                        VALUES (
                            :user_id, :name, :email, :contact_number, :role,
                            :account_id, :team_id, 1, NOW(), NOW()
                        )
                    """)
                    db.session.execute(insert_query, {
                        'user_id': user.id,
                        'name': user.username,
                        'email': user.email,
                        'contact_number': '+1-000-000-0000',
                        'role': 'Engineer',
                        'account_id': user.account_id,
                        'team_id': user.team_id
                    })
                    print(f"   ✅ Created TeamMember for {user.username}")
                else:
                    print(f"   ✅ {user.username} already has TeamMember")
            
            db.session.commit()
            print("   ✅ All TeamMember records committed!")
            
        except Exception as e:
            db.session.rollback()
            print(f"   ❌ Error creating TeamMembers: {e}")
        
        # Step 3: Verify TeamMember creation
        print("\n3️⃣ VERIFICATION:")
        verify_query = text("""
            SELECT 
                u.id, u.username, tm.id as team_member_id, tm.role, tm.is_active
            FROM user u
            LEFT JOIN team_member tm ON u.id = tm.user_id
            WHERE u.username IN ('testuser1', 'testuser2')
            ORDER BY u.username
        """)
        verified = db.session.execute(verify_query).fetchall()
        
        for user in verified:
            if user.team_member_id:
                print(f"   ✅ {user.username}: TeamMember ID={user.team_member_id}, Role={user.role}, Active={user.is_active}")
            else:
                print(f"   ❌ {user.username}: Still missing TeamMember!")
        
        # Step 4: Check recent handovers with correct column names
        print("\n4️⃣ CHECKING RECENT HANDOVERS:")
        try:
            handover_query = text("""
                SELECT 
                    hr.id, hr.created_by_id, hr.shift_date, hr.current_shift_type,
                    hr.next_shift_type, hr.status, hr.created_at,
                    u1.username as created_by_user
                FROM handover_request hr
                JOIN user u1 ON hr.created_by_id = u1.id
                WHERE hr.account_id = 1 AND hr.team_id = 2
                ORDER BY hr.created_at DESC
                LIMIT 5
            """)
            handovers = db.session.execute(handover_query).fetchall()
            
            if handovers:
                for h in handovers:
                    print(f"   Handover ID={h.id}: {h.created_by_user}")
                    print(f"      Date: {h.shift_date}, Status: {h.status}")
                    print(f"      Shift: {h.current_shift_type} → {h.next_shift_type}")
                    print(f"      Created: {h.created_at}")
                    print()
            else:
                print("   ℹ️ No handovers found")
        except Exception as e:
            print(f"   ❌ Error checking handovers: {e}")
        
        # Step 5: Check handover notifications
        print("5️⃣ CHECKING NOTIFICATIONS:")
        try:
            notif_query = text("""
                SELECT 
                    hn.id, hn.user_id, hn.notification_type, hn.is_read,
                    hn.created_at, u.username
                FROM handover_notification hn
                JOIN user u ON hn.user_id = u.id
                WHERE hn.account_id = 1 AND hn.team_id = 2
                ORDER BY hn.created_at DESC
                LIMIT 5
            """)
            notifications = db.session.execute(notif_query).fetchall()
            
            if notifications:
                for n in notifications:
                    print(f"   Notification ID={n.id}: {n.notification_type} for {n.username}")
                    print(f"      Read: {n.is_read}, Created: {n.created_at}")
            else:
                print("   ℹ️ No notifications found")
        except Exception as e:
            print(f"   ❌ Error checking notifications: {e}")
        
        # Step 6: Check incident assignments
        print("\n6️⃣ CHECKING INCIDENT ASSIGNMENTS:")
        try:
            assign_query = text("""
                SELECT 
                    ia.id, ia.incident_title, ia.assigned_to_email,
                    ia.assigned_by_email, ia.created_at
                FROM incident_assignment ia
                ORDER BY ia.created_at DESC
                LIMIT 5
            """)
            assignments = db.session.execute(assign_query).fetchall()
            
            if assignments:
                for a in assignments:
                    print(f"   Assignment ID={a.id}: {a.incident_title}")
                    print(f"      To: {a.assigned_to_email}, By: {a.assigned_by_email}")
                    print(f"      Created: {a.created_at}")
                    print()
            else:
                print("   ℹ️ No incident assignments found")
        except Exception as e:
            print(f"   ❌ Error checking assignments: {e}")
        
        print("\n" + "=" * 60)
        print("🎯 TeamMember fix and flow check complete!")
        print("\n📋 NEXT STEPS:")
        print("   1. Try submitting a new handover with testuser1 → testuser2")
        print("   2. Check if notifications appear on testuser2's dashboard")
        print("   3. Verify incident assignments show correct emails")

if __name__ == "__main__":
    fix_team_members_and_check_flow()