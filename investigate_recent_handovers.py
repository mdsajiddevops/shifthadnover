#!/usr/bin/env python3

"""
Investigate recent handover submissions and clean up problematic assignments
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

def investigate_recent_handovers():
    """Investigate and fix recent handover submissions with invalid assignments"""
    
    with app.app_context():
        print("🔍 INVESTIGATING RECENT HANDOVER ISSUES")
        print("=" * 60)
        
        # Step 1: Check recent incidents with invalid assignments
        print("\n1️⃣ CHECKING RECENT INCIDENTS WITH INVALID ASSIGNMENTS:")
        
        invalid_assignments_query = text("""
            SELECT i.id, i.title, i.assigned_to, i.shift_id, i.type, s.submitted_at
            FROM incident i
            JOIN shift s ON i.shift_id = s.id
            WHERE s.account_id = 1 AND s.team_id = 2
            AND i.assigned_to IS NOT NULL
            AND i.assigned_to NOT IN (
                SELECT CAST(tm.id AS CHAR) FROM team_member tm 
                WHERE tm.account_id = 1 AND tm.team_id = 2 AND tm.user_id IS NOT NULL
            )
            ORDER BY s.submitted_at DESC, i.id DESC
        """)
        
        invalid_incidents = db.session.execute(invalid_assignments_query).fetchall()
        
        print(f"   Found {len(invalid_incidents)} incidents with invalid assignments:")
        for inc in invalid_incidents:
            print(f"   ❌ Incident {inc.id}: '{inc.title}' → assigned_to='{inc.assigned_to}' (INVALID)")
            print(f"      Shift: {inc.shift_id}, Type: {inc.type}, Submitted: {inc.submitted_at}")
        
        # Step 2: Check what valid TeamMember IDs should be used
        print("\n2️⃣ VALID TEAMMEMBER IDS FOR ASSIGNMENTS:")
        
        valid_tm_query = text("""
            SELECT tm.id, tm.name, u.username
            FROM team_member tm
            JOIN user u ON tm.user_id = u.id
            WHERE tm.account_id = 1 AND tm.team_id = 2
            AND tm.name LIKE 'techopsuser%'
            ORDER BY tm.name
        """)
        
        valid_tms = db.session.execute(valid_tm_query).fetchall()
        
        print(f"   Valid TeamMember IDs for assignments:")
        for tm in valid_tms:
            print(f"   ✅ ID={tm.id}: '{tm.name}' → {tm.username}")
        
        # Step 3: Fix invalid assignments
        print("\n3️⃣ FIXING INVALID ASSIGNMENTS:")
        
        if invalid_incidents:
            print(f"   🔧 Fixing {len(invalid_incidents)} invalid assignments...")
            
            # Map old invalid IDs to new valid ones
            assignment_fixes = {
                '31': '37',  # old techopsuser2 → new techopsuser2
                '32': '36',  # old techopsuser1 → new techopsuser1
                '33': '38',  # old techopsuser3 → new techopsuser3
                '34': '39',  # old techopsuser4 → new techopsuser4
            }
            
            fixed_count = 0
            for inc in invalid_incidents:
                old_assignment = inc.assigned_to
                new_assignment = assignment_fixes.get(old_assignment)
                
                if new_assignment:
                    # Update the incident assignment
                    update_query = text("""
                        UPDATE incident 
                        SET assigned_to = :new_assignment 
                        WHERE id = :incident_id
                    """)
                    
                    db.session.execute(update_query, {
                        'new_assignment': new_assignment,
                        'incident_id': inc.id
                    })
                    
                    print(f"   ✅ Fixed Incident {inc.id}: '{old_assignment}' → '{new_assignment}'")
                    fixed_count += 1
                else:
                    print(f"   ⚠️ No fix mapping for assignment: {old_assignment}")
            
            if fixed_count > 0:
                try:
                    db.session.commit()
                    print(f"   🎉 Successfully fixed {fixed_count} incident assignments")
                except Exception as e:
                    print(f"   ❌ Error fixing assignments: {e}")
                    db.session.rollback()
        
        # Step 4: Create missing notifications for corrected assignments
        print("\n4️⃣ CREATING MISSING NOTIFICATIONS:")
        
        # Get recent incidents that should have notifications
        recent_assigned_query = text("""
            SELECT DISTINCT i.id, i.title, i.assigned_to, i.shift_id, s.submitted_at,
                   tm.name as assignee_name, u.id as user_id, u.username
            FROM incident i
            JOIN shift s ON i.shift_id = s.id
            JOIN team_member tm ON CAST(tm.id AS CHAR) = i.assigned_to
            JOIN user u ON tm.user_id = u.id
            WHERE s.account_id = 1 AND s.team_id = 2
            AND i.assigned_to IS NOT NULL
            AND s.submitted_at >= DATE_SUB(NOW(), INTERVAL 1 DAY)
            ORDER BY s.submitted_at DESC, i.id DESC
        """)
        
        recent_assignments = db.session.execute(recent_assigned_query).fetchall()
        
        print(f"   Found {len(recent_assignments)} recent valid assignments:")
        
        notifications_created = 0
        for assignment in recent_assignments:
            print(f"   📋 Incident: '{assignment.title}' → {assignment.assignee_name}")
            
            # Check if notification already exists
            existing_notif_query = text("""
                SELECT id FROM handover_notification 
                WHERE recipient_id = :user_id 
                AND title LIKE :title_pattern
                LIMIT 1
            """)
            
            existing = db.session.execute(existing_notif_query, {
                'user_id': assignment.user_id,
                'title_pattern': f'%{assignment.title}%'
            }).fetchone()
            
            if not existing:
                # Create missing notification
                create_notif_query = text("""
                    INSERT INTO handover_notification 
                    (recipient_id, handover_request_id, notification_type, title, message, 
                     action_url, action_text, account_id, team_id, is_read, is_dismissed, created_at)
                    VALUES (:recipient_id, :handover_request_id, 'incident_assigned', :title, :message,
                            '/notifications', 'View Assignment', 1, 2, 0, 0, NOW())
                """)
                
                db.session.execute(create_notif_query, {
                    'recipient_id': assignment.user_id,
                    'handover_request_id': assignment.shift_id,
                    'title': f'New Incident Assignment: {assignment.title}',
                    'message': f'You have been assigned to handle incident: {assignment.title}'
                })
                
                print(f"      ✅ Created notification for {assignment.username}")
                notifications_created += 1
            else:
                print(f"      ✓ Notification already exists")
        
        if notifications_created > 0:
            try:
                db.session.commit()
                print(f"\n   🎉 Successfully created {notifications_created} missing notifications")
            except Exception as e:
                print(f"\n   ❌ Error creating notifications: {e}")
                db.session.rollback()
        
        # Step 5: Verify the fix
        print("\n5️⃣ VERIFICATION AFTER FIXES:")
        
        # Check notifications for techopsuser2
        techopsuser2_notif_query = text("""
            SELECT hn.id, hn.title, hn.created_at, hn.is_read
            FROM handover_notification hn
            JOIN user u ON hn.recipient_id = u.id
            WHERE u.username = 'techopsuser2'
            ORDER BY hn.created_at DESC
            LIMIT 5
        """)
        
        techopsuser2_notifs = db.session.execute(techopsuser2_notif_query).fetchall()
        
        print(f"   📬 techopsuser2 now has {len(techopsuser2_notifs)} notifications:")
        for notif in techopsuser2_notifs:
            status = "📖 READ" if notif.is_read else "📧 UNREAD"
            print(f"      {status} {notif.title} ({notif.created_at})")
        
        print("\n" + "=" * 60)
        print("🎯 INVESTIGATION AND FIXES COMPLETE")
        
        if fixed_count > 0 or notifications_created > 0:
            print("\n✅ FIXES APPLIED:")
            if fixed_count > 0:
                print(f"   • Fixed {fixed_count} invalid incident assignments")
            if notifications_created > 0:
                print(f"   • Created {notifications_created} missing notifications")
            print("\n🚀 Test handover submission now - notifications should work!")
        else:
            print("\n✅ No fixes needed - system is clean")

if __name__ == "__main__":
    investigate_recent_handovers()