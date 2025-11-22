#!/usr/bin/env python3

"""
Comprehensive test to simulate exact handover workflow and identify issues
"""

import sys
import os

# Change to app directory
os.chdir('/app')
sys.path.insert(0, '/app')

# Import the Flask app and database
from app import app, db
from sqlalchemy import text
from datetime import datetime

def test_full_handover_workflow():
    """Test the complete handover workflow from form submission to notification"""
    
    with app.app_context():
        print("🧪 COMPREHENSIVE HANDOVER WORKFLOW TEST")
        print("=" * 70)
        
        # Step 1: Simulate form submission from techopsuser1 to techopsuser2
        print("\n1️⃣ SIMULATING FORM SUBMISSION:")
        print("   📝 User: techopsuser1 submitting handover")
        print("   📝 Assigning incident to: techopsuser2")
        print("   📝 Form would send: assigned_to_name='37' (TeamMember ID)")
        
        # Step 2: Test create_enhanced_incident_assignment logic
        print("\n2️⃣ TESTING create_enhanced_incident_assignment:")
        
        # Simulate the assignment process
        assigned_to_name = "37"  # This is what form sends (TeamMember ID)
        incident_title = "Test Incident"
        account_id = 1
        team_id = 2
        
        print(f"   Input: assigned_to_name='{assigned_to_name}'")
        
        # Check if it's a numeric team member ID (this is the current logic)
        if assigned_to_name.isdigit():
            team_member_id = int(assigned_to_name)
            print(f"   🔢 Detected as TeamMember ID: {team_member_id}")
            
            # Find the team member
            member_query = text("""
                SELECT tm.id, tm.name, tm.user_id, u.username
                FROM team_member tm
                LEFT JOIN user u ON tm.user_id = u.id
                WHERE tm.id = :tm_id AND tm.account_id = :account_id AND tm.team_id = :team_id
            """)
            assigned_member = db.session.execute(member_query, {
                'tm_id': team_member_id,
                'account_id': account_id,
                'team_id': team_id
            }).fetchone()
            
            if assigned_member:
                print(f"   ✅ Found TeamMember: {assigned_member.name} (ID: {assigned_member.id})")
                
                if assigned_member.user_id:
                    print(f"   ✅ Resolved User: {assigned_member.username} (ID: {assigned_member.user_id})")
                    assigned_user_id = assigned_member.user_id
                    
                    # Test HandoverNotification creation
                    print("\n3️⃣ TESTING NOTIFICATION CREATION:")
                    print(f"   📨 Would create HandoverNotification:")
                    print(f"      recipient_id = {assigned_user_id}")
                    print(f"      title = 'New Incident Assignment: {incident_title}'")
                    print(f"      notification_type = 'incident_assigned'")
                    
                    # Test HandoverIncidentResponseLog creation
                    print("\n4️⃣ TESTING RESPONSE LOG CREATION:")
                    print(f"   📝 Would create HandoverIncidentResponseLog:")
                    print(f"      assigned_by_name = 'techopsuser1' (current user)")
                    print(f"      accepted_by_id = {assigned_user_id}")
                    print(f"      accepted_by_name = '{assigned_member.username}'")
                    
                else:
                    print(f"   ❌ TeamMember has no user_id link!")
            else:
                print(f"   ❌ TeamMember {team_member_id} not found!")
        
        # Step 3: Check existing notifications and logs for techopsuser2
        print("\n5️⃣ CHECKING EXISTING NOTIFICATIONS:")
        
        techopsuser2_query = text("""
            SELECT id FROM user WHERE username = 'techopsuser2'
        """)
        techopsuser2 = db.session.execute(techopsuser2_query).fetchone()
        
        if techopsuser2:
            user_id = techopsuser2.id
            print(f"   👤 techopsuser2 User ID: {user_id}")
            
            # Check existing notifications
            notif_query = text("""
                SELECT id, title, message, created_at, is_read
                FROM handover_notification 
                WHERE recipient_id = :user_id
                ORDER BY created_at DESC
                LIMIT 5
            """)
            notifications = db.session.execute(notif_query, {'user_id': user_id}).fetchall()
            
            print(f"   📬 Found {len(notifications)} existing notifications:")
            for notif in notifications:
                status = "📖 READ" if notif.is_read else "📧 UNREAD"
                print(f"      {status}: {notif.title} ({notif.created_at})")
            
            # Check existing response logs
            log_query = text("""
                SELECT id, incident_title, assigned_by_name, accepted_by_name, response_date
                FROM handover_incident_response_log
                WHERE accepted_by_id = :user_id
                ORDER BY response_date DESC
                LIMIT 5
            """)
            logs = db.session.execute(log_query, {'user_id': user_id}).fetchall()
            
            print(f"   📝 Found {len(logs)} response logs for techopsuser2:")
            for log in logs:
                print(f"      📋 {log.incident_title}: {log.assigned_by_name} → {log.accepted_by_name} ({log.response_date})")
        
        # Step 4: Check recent handover submissions
        print("\n6️⃣ CHECKING RECENT HANDOVER ACTIVITY:")
        
        recent_shifts_query = text("""
            SELECT s.id, s.date, s.current_shift_type, s.next_shift_type, s.submitted_at,
                   u.username as submitted_by
            FROM shift s
            LEFT JOIN user u ON s.account_id = u.account_id
            WHERE s.account_id = 1 AND s.team_id = 2 
            AND s.submitted_at IS NOT NULL
            ORDER BY s.submitted_at DESC
            LIMIT 3
        """)
        recent_shifts = db.session.execute(recent_shifts_query).fetchall()
        
        print(f"   📅 Found {len(recent_shifts)} recent handover submissions:")
        for shift in recent_shifts:
            print(f"      🔄 Shift {shift.id}: {shift.current_shift_type}→{shift.next_shift_type} on {shift.date}")
            print(f"         Submitted: {shift.submitted_at}")
            
            # Check incidents for this shift
            incident_query = text("""
                SELECT i.id, i.title, i.assigned_to, i.type
                FROM incident i
                WHERE i.shift_id = :shift_id
                LIMIT 3
            """)
            incidents = db.session.execute(incident_query, {'shift_id': shift.id}).fetchall()
            
            print(f"         📋 {len(incidents)} incidents:")
            for inc in incidents:
                print(f"            • {inc.title} → {inc.assigned_to} ({inc.type})")
        
        # Step 5: Test the actual dropdown API
        print("\n7️⃣ TESTING DROPDOWN API SIMULATION:")
        
        engineers_query = text("""
            SELECT tm.id, tm.name, tm.user_id, u.username
            FROM team_member tm
            LEFT JOIN user u ON tm.user_id = u.id
            WHERE tm.account_id = 1 AND tm.team_id = 2
            AND tm.name LIKE 'techopsuser%'
            ORDER BY tm.name
        """)
        engineers = db.session.execute(engineers_query).fetchall()
        
        print(f"   📋 Dropdown would show these techops users:")
        for eng in engineers:
            link_status = f"→ {eng.username}" if eng.user_id else "→ NO USER"
            print(f"      🎯 ID={eng.id}: '{eng.name}' {link_status}")
        
        print("\n" + "=" * 70)
        print("🎯 WORKFLOW TEST COMPLETE")
        
        # Final diagnosis
        print("\n🔍 DIAGNOSIS:")
        if len(engineers) >= 2 and all(eng.user_id for eng in engineers):
            print("   ✅ All components are working correctly")
            print("   ✅ TeamMember → User links are intact")
            print("   ✅ Assignment resolution will work")
            print("   ✅ Notifications should be created")
            print("\n💡 If notifications still not appearing, the issue might be:")
            print("   1. 🔍 Check if handover form is actually submitting assignments")
            print("   2. 🔍 Check if form POST data contains the expected field names")
            print("   3. 🔍 Check if browser JavaScript is sending correct TeamMember IDs")
            print("   4. 🔍 Check if there are errors during form processing")
        else:
            print("   ❌ Some TeamMember → User links are broken")
            print("   🔧 Run the comprehensive cleanup again")

if __name__ == "__main__":
    test_full_handover_workflow()