#!/usr/bin/env python3

"""
Debug fresh handover submission flow for testuser1 -> testuser2
"""

import sys
import os

# Change to app directory
os.chdir('/app')
sys.path.insert(0, '/app')

# Import the Flask app and database
from app import app, db
from sqlalchemy import text

def debug_fresh_handover_flow():
    """Debug the complete handover flow for testuser1 -> testuser2"""
    
    with app.app_context():
        print("🔍 Debugging fresh handover flow for testuser1 -> testuser2")
        print("=" * 70)
        
        # Step 1: Verify user configurations
        print("\n1️⃣ USER CONFIGURATION CHECK:")
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
            print(f"   {user.username}: ID={user.id}, Email={user.email}, Account={user.account_id}, Team={user.team_id}, TeamMember={user.team_member_id}")
        
        # Step 2: Check most recent handover requests
        print("\n2️⃣ RECENT HANDOVER REQUESTS:")
        handover_query = text("""
            SELECT 
                hr.id, hr.incident_title, hr.assigned_to, hr.created_by,
                hr.created_at, hr.account_id, hr.team_id,
                u1.username as created_by_user,
                u2.username as assigned_to_user
            FROM handover_request hr
            JOIN user u1 ON hr.created_by = u1.id
            JOIN user u2 ON hr.assigned_to = u2.id
            WHERE hr.account_id = 1 AND hr.team_id = 2
            ORDER BY hr.created_at DESC
            LIMIT 5
        """)
        handovers = db.session.execute(handover_query).fetchall()
        
        if handovers:
            for handover in handovers:
                print(f"   ID={handover.id}: {handover.incident_title}")
                print(f"      From: {handover.created_by_user} (ID={handover.created_by})")
                print(f"      To: {handover.assigned_to_user} (ID={handover.assigned_to})")
                print(f"      Created: {handover.created_at}")
                print()
        else:
            print("   ❌ No handover requests found!")
        
        # Step 3: Check handover notifications
        print("3️⃣ HANDOVER NOTIFICATIONS:")
        notification_query = text("""
            SELECT 
                hn.id, hn.handover_request_id, hn.user_id, hn.notification_type,
                hn.created_at, hn.is_read,
                u.username as notified_user
            FROM handover_notification hn
            JOIN user u ON hn.user_id = u.id
            WHERE hn.account_id = 1 AND hn.team_id = 2
            ORDER BY hn.created_at DESC
            LIMIT 10
        """)
        notifications = db.session.execute(notification_query).fetchall()
        
        if notifications:
            for notif in notifications:
                print(f"   ID={notif.id}: {notif.notification_type} for {notif.notified_user}")
                print(f"      Handover ID: {notif.handover_request_id}, Read: {notif.is_read}")
                print(f"      Created: {notif.created_at}")
                print()
        else:
            print("   ❌ No handover notifications found!")
        
        # Step 4: Check incident assignments
        print("4️⃣ INCIDENT ASSIGNMENTS:")
        assignment_query = text("""
            SELECT 
                ia.id, ia.incident_title, ia.assigned_to_email, 
                ia.assigned_by_email, ia.created_at,
                ia.shift_id, ia.handover_request_id
            FROM incident_assignment ia
            WHERE ia.handover_request_id IN (
                SELECT hr.id FROM handover_request hr 
                WHERE hr.account_id = 1 AND hr.team_id = 2
            )
            ORDER BY ia.created_at DESC
            LIMIT 10
        """)
        assignments = db.session.execute(assignment_query).fetchall()
        
        if assignments:
            for assignment in assignments:
                print(f"   ID={assignment.id}: {assignment.incident_title}")
                print(f"      Assigned to: {assignment.assigned_to_email}")
                print(f"      Assigned by: {assignment.assigned_by_email}")
                print(f"      Handover ID: {assignment.handover_request_id}")
                print(f"      Created: {assignment.created_at}")
                print()
        else:
            print("   ❌ No incident assignments found!")
        
        # Step 5: Check response logs
        print("5️⃣ INCIDENT RESPONSE LOGS:")
        log_query = text("""
            SELECT 
                hirl.id, hirl.incident_title, hirl.assigned_to_email,
                hirl.response_log, hirl.created_at,
                hirl.handover_id, hirl.from_shift_id, hirl.to_shift_id
            FROM handover_incident_response_log hirl
            WHERE hirl.handover_id IN (
                SELECT hr.id FROM handover_request hr 
                WHERE hr.account_id = 1 AND hr.team_id = 2
            )
            ORDER BY hirl.created_at DESC
            LIMIT 5
        """)
        logs = db.session.execute(log_query).fetchall()
        
        if logs:
            for log in logs:
                print(f"   ID={log.id}: {log.incident_title}")
                print(f"      Assigned to: {log.assigned_to_email}")
                print(f"      Response: {log.response_log[:100]}...")
                print(f"      Handover ID: {log.handover_id}")
                print(f"      Created: {log.created_at}")
                print()
        else:
            print("   ❌ No incident response logs found!")
        
        # Step 6: Check current shifts
        print("6️⃣ CURRENT SHIFTS:")
        shift_query = text("""
            SELECT 
                s.id, s.shift_date, s.shift_type, s.account_id, s.team_id,
                s.created_at
            FROM shift s
            WHERE s.account_id = 1 AND s.team_id = 2
            ORDER BY s.created_at DESC
            LIMIT 3
        """)
        shifts = db.session.execute(shift_query).fetchall()
        
        if shifts:
            for shift in shifts:
                print(f"   ID={shift.id}: {shift.shift_type} on {shift.shift_date}")
                print(f"      Account: {shift.account_id}, Team: {shift.team_id}")
                print(f"      Created: {shift.created_at}")
                print()
        else:
            print("   ❌ No shifts found!")
        
        print("=" * 70)
        print("🎯 Debug analysis complete!")
        
        # Summary analysis
        print("\n📊 ANALYSIS SUMMARY:")
        if not handovers:
            print("   🚨 ISSUE: No handover requests found - handover creation failing")
        elif not notifications:
            print("   🚨 ISSUE: Handovers created but notifications not generated")
        elif not assignments:
            print("   🚨 ISSUE: Notifications created but incident assignments missing")
        else:
            print("   ✅ Data flow appears normal - check specific user filtering")

if __name__ == "__main__":
    debug_fresh_handover_flow()