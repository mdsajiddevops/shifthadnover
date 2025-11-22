#!/usr/bin/env python3

"""
Fix missing TeamMember records for testuser1 and testuser2
"""

import sys
import os

# Change to app directory
os.chdir('/app')
sys.path.insert(0, '/app')

# Import the Flask app and database
from app import app, db
from sqlalchemy import text

def fix_team_member_records():
    """Fix missing TeamMember records for testuser1 and testuser2"""
    
    with app.app_context():
        print("🔧 Fixing missing TeamMember records for testuser1 and testuser2")
        print("=" * 60)
        
        # Step 1: Check current state
        print("\n1️⃣ CURRENT STATE CHECK:")
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
            print(f"   {user.username}: ID={user.id}, TeamMember={tm_status}")
        
        # Step 2: Check handover_request table structure
        print("\n2️⃣ CHECKING TABLE STRUCTURES:")
        try:
            # Check handover_request columns
            hr_columns_query = text("SHOW COLUMNS FROM handover_request")
            hr_columns = db.session.execute(hr_columns_query).fetchall()
            print("   handover_request columns:")
            for col in hr_columns:
                print(f"      {col[0]} ({col[1]})")
        except Exception as e:
            print(f"   ❌ Error checking handover_request: {e}")
        
        # Step 3: Check team_member table structure
        try:
            tm_columns_query = text("SHOW COLUMNS FROM team_member")
            tm_columns = db.session.execute(tm_columns_query).fetchall()
            print("   team_member columns:")
            for col in tm_columns:
                print(f"      {col[0]} ({col[1]})")
        except Exception as e:
            print(f"   ❌ Error checking team_member: {e}")
        
        # Step 4: Create missing TeamMember records
        print("\n3️⃣ CREATING MISSING TEAMMEMBER RECORDS:")
        try:
            for user in users:
                if not user.team_member_id:
                    # Create TeamMember record
                    insert_query = text("""
                        INSERT INTO team_member (user_id, team_id, account_id, role, created_at)
                        VALUES (:user_id, :team_id, :account_id, 'Engineer', NOW())
                    """)
                    db.session.execute(insert_query, {
                        'user_id': user.id,
                        'team_id': user.team_id,
                        'account_id': user.account_id
                    })
                    print(f"   ✅ Created TeamMember record for {user.username}")
                else:
                    print(f"   ✅ {user.username} already has TeamMember record")
            
            db.session.commit()
            print("   ✅ All TeamMember records committed!")
            
        except Exception as e:
            db.session.rollback()
            print(f"   ❌ Error creating TeamMember records: {e}")
        
        # Step 5: Verify fix
        print("\n4️⃣ VERIFICATION:")
        verify_query = text("""
            SELECT 
                u.id, u.username, u.email, u.account_id, u.team_id,
                tm.id as team_member_id, tm.role
            FROM user u
            LEFT JOIN team_member tm ON u.id = tm.user_id
            WHERE u.username IN ('testuser1', 'testuser2')
            ORDER BY u.username
        """)
        verified_users = db.session.execute(verify_query).fetchall()
        
        for user in verified_users:
            if user.team_member_id:
                print(f"   ✅ {user.username}: TeamMember ID={user.team_member_id}, Role={user.role}")
            else:
                print(f"   ❌ {user.username}: Still missing TeamMember record!")
        
        # Step 6: Check recent handovers (with correct column names)
        print("\n5️⃣ CHECKING RECENT HANDOVERS:")
        try:
            # Use correct column names
            handover_query = text("""
                SELECT 
                    hr.id, hr.created_by, hr.assigned_to,
                    hr.created_at, hr.account_id, hr.team_id,
                    u1.username as created_by_user,
                    u2.username as assigned_to_user
                FROM handover_request hr
                JOIN user u1 ON hr.created_by = u1.id
                JOIN user u2 ON hr.assigned_to = u2.id
                WHERE hr.account_id = 1 AND hr.team_id = 2
                ORDER BY hr.created_at DESC
                LIMIT 3
            """)
            handovers = db.session.execute(handover_query).fetchall()
            
            if handovers:
                for handover in handovers:
                    print(f"   Handover ID={handover.id}: {handover.created_by_user} → {handover.assigned_to_user}")
                    print(f"      Created: {handover.created_at}")
            else:
                print("   ℹ️ No recent handovers found")
        except Exception as e:
            print(f"   ❌ Error checking handovers: {e}")
        
        print("\n" + "=" * 60)
        print("🎯 TeamMember fix operation complete!")

if __name__ == "__main__":
    fix_team_member_records()