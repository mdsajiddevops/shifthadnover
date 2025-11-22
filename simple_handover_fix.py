#!/usr/bin/env python3

"""
Simple investigation and fix for handover issues without complex SQL
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

def simple_handover_fix():
    """Simple investigation and fix for handover issues"""
    
    with app.app_context():
        print("🔧 SIMPLE HANDOVER ISSUE FIX")
        print("=" * 50)
        
        # Step 1: Get current valid TeamMember IDs
        print("\n1️⃣ CURRENT VALID TEAMMEMBER IDS:")
        
        valid_tm_query = text("""
            SELECT tm.id, tm.name, u.username
            FROM team_member tm
            JOIN user u ON tm.user_id = u.id
            WHERE tm.account_id = 1 AND tm.team_id = 2
            AND tm.name LIKE 'techopsuser%'
            ORDER BY tm.name
        """)
        
        valid_tms = db.session.execute(valid_tm_query).fetchall()
        
        print(f"   Valid TeamMember IDs:")
        for tm in valid_tms:
            print(f"   ✅ ID={tm.id}: '{tm.name}' → {tm.username}")
        
        # Step 2: Check recent incidents
        print("\n2️⃣ CHECKING RECENT INCIDENTS:")
        
        recent_incidents_query = text("""
            SELECT i.id, i.title, i.assigned_to, i.shift_id, i.type
            FROM incident i
            JOIN shift s ON i.shift_id = s.id
            WHERE s.account_id = 1 AND s.team_id = 2
            AND i.assigned_to IS NOT NULL
            AND s.submitted_at >= DATE_SUB(NOW(), INTERVAL 1 DAY)
            ORDER BY i.id DESC
            LIMIT 10
        """)
        
        recent_incidents = db.session.execute(recent_incidents_query).fetchall()
        
        print(f"   Found {len(recent_incidents)} recent incidents with assignments:")
        
        # Check which ones need fixing
        valid_tm_ids = {str(tm.id) for tm in valid_tms}
        incidents_to_fix = []
        
        for inc in recent_incidents:
            if inc.assigned_to in valid_tm_ids:
                print(f"   ✅ Incident {inc.id}: '{inc.title}' → {inc.assigned_to} (VALID)")
            else:
                print(f"   ❌ Incident {inc.id}: '{inc.title}' → {inc.assigned_to} (INVALID - needs fix)")
                incidents_to_fix.append(inc)
        
        # Step 3: Fix invalid assignments
        if incidents_to_fix:
            print(f"\n3️⃣ FIXING {len(incidents_to_fix)} INVALID ASSIGNMENTS:")
            
            # Simple mapping of old IDs to new IDs
            fixes = {
                '31': '37',  # techopsuser2
                '32': '36',  # techopsuser1
                '33': '38',  # techopsuser3
                '34': '39',  # techopsuser4
                '2': '36',   # fallback to techopsuser1
                '3': '37',   # fallback to techopsuser2
            }
            
            fixed_count = 0
            for inc in incidents_to_fix:
                new_assignment = fixes.get(inc.assigned_to)
                
                if new_assignment:
                    update_query = text("""
                        UPDATE incident 
                        SET assigned_to = :new_assignment 
                        WHERE id = :incident_id
                    """)
                    
                    db.session.execute(update_query, {
                        'new_assignment': new_assignment,
                        'incident_id': inc.id
                    })
                    
                    print(f"   ✅ Fixed Incident {inc.id}: '{inc.assigned_to}' → '{new_assignment}'")
                    fixed_count += 1
                else:
                    # Default to techopsuser2 if no mapping found
                    default_assignment = '37'
                    update_query = text("""
                        UPDATE incident 
                        SET assigned_to = :new_assignment 
                        WHERE id = :incident_id
                    """)
                    
                    db.session.execute(update_query, {
                        'new_assignment': default_assignment,
                        'incident_id': inc.id
                    })
                    
                    print(f"   ✅ Fixed Incident {inc.id}: '{inc.assigned_to}' → '{default_assignment}' (default)")
                    fixed_count += 1
            
            if fixed_count > 0:
                try:
                    db.session.commit()
                    print(f"   🎉 Successfully fixed {fixed_count} incident assignments")
                except Exception as e:
                    print(f"   ❌ Error fixing assignments: {e}")
                    db.session.rollback()
                    return
        
        # Step 4: Create notifications for techopsuser2
        print("\n4️⃣ CREATING NOTIFICATIONS FOR TECHOPSUSER2:")
        
        # Find techopsuser2
        techopsuser2_query = text("""
            SELECT u.id, u.username FROM user u WHERE u.username = 'techopsuser2'
        """)
        techopsuser2 = db.session.execute(techopsuser2_query).fetchone()
        
        if not techopsuser2:
            print("   ❌ techopsuser2 not found!")
            return
        
        print(f"   👤 techopsuser2 User ID: {techopsuser2.id}")
        
        # Get recent incidents assigned to techopsuser2's TeamMember ID (37)
        techopsuser2_incidents_query = text("""
            SELECT DISTINCT i.id, i.title, i.shift_id
            FROM incident i
            JOIN shift s ON i.shift_id = s.id
            WHERE s.account_id = 1 AND s.team_id = 2
            AND i.assigned_to = '37'
            AND s.submitted_at >= DATE_SUB(NOW(), INTERVAL 1 DAY)
        """)
        
        techopsuser2_incidents = db.session.execute(techopsuser2_incidents_query).fetchall()
        
        print(f"   📋 Found {len(techopsuser2_incidents)} incidents assigned to techopsuser2")
        
        notifications_created = 0
        for inc in techopsuser2_incidents:
            # Check if notification already exists
            existing_notif_query = text("""
                SELECT id FROM handover_notification 
                WHERE recipient_id = :user_id 
                AND title LIKE :title_pattern
                LIMIT 1
            """)
            
            existing = db.session.execute(existing_notif_query, {
                'user_id': techopsuser2.id,
                'title_pattern': f'%{inc.title}%'
            }).fetchone()
            
            if not existing:
                # Create notification
                create_notif_query = text("""
                    INSERT INTO handover_notification 
                    (recipient_id, handover_request_id, notification_type, title, message, 
                     action_url, action_text, account_id, team_id, is_read, is_dismissed, created_at)
                    VALUES (:recipient_id, :handover_request_id, 'incident_assigned', :title, :message,
                            '/notifications', 'View Assignment', 1, 2, 0, 0, NOW())
                """)
                
                db.session.execute(create_notif_query, {
                    'recipient_id': techopsuser2.id,
                    'handover_request_id': inc.shift_id,
                    'title': f'New Incident Assignment: {inc.title}',
                    'message': f'You have been assigned to handle incident: {inc.title}'
                })
                
                print(f"   ✅ Created notification for: {inc.title}")
                notifications_created += 1
            else:
                print(f"   ✓ Notification already exists for: {inc.title}")
        
        if notifications_created > 0:
            try:
                db.session.commit()
                print(f"   🎉 Successfully created {notifications_created} notifications")
            except Exception as e:
                print(f"   ❌ Error creating notifications: {e}")
                db.session.rollback()
                return
        
        # Step 5: Verify notifications for techopsuser2
        print("\n5️⃣ VERIFICATION - TECHOPSUSER2 NOTIFICATIONS:")
        
        final_notif_query = text("""
            SELECT hn.id, hn.title, hn.created_at, hn.is_read
            FROM handover_notification hn
            WHERE hn.recipient_id = :user_id
            ORDER BY hn.created_at DESC
            LIMIT 5
        """)
        
        final_notifs = db.session.execute(final_notif_query, {
            'user_id': techopsuser2.id
        }).fetchall()
        
        print(f"   📬 techopsuser2 now has {len(final_notifs)} notifications:")
        for notif in final_notifs:
            status = "📖 READ" if notif.is_read else "📧 UNREAD"
            print(f"      {status} {notif.title}")
            print(f"         Created: {notif.created_at}")
        
        print("\n" + "=" * 50)
        print("🎯 SIMPLE FIX COMPLETE")
        
        if fixed_count > 0 or notifications_created > 0:
            print("\n✅ CHANGES MADE:")
            if fixed_count > 0:
                print(f"   • Fixed {fixed_count} invalid incident assignments")
            if notifications_created > 0:
                print(f"   • Created {notifications_created} missing notifications")
            print(f"   • techopsuser2 now has {len(final_notifs)} total notifications")
            print("\n🚀 LOGIN AS TECHOPSUSER2 TO SEE NOTIFICATIONS!")
        else:
            print("\n✅ No fixes needed - system is already clean")

if __name__ == "__main__":
    simple_handover_fix()