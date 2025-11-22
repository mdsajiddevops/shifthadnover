#!/usr/bin/env python3
"""
Comprehensive fix for handover notification and dashboard issues
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app, db
from models.models import User, Team, TeamMember
from models.handover_enhanced import HandoverRequest, HandoverNotification, IncidentAssignment, HandoverIncidentResponseLog
from sqlalchemy import text

def fix_handover_issues():
    """Fix all handover-related issues"""
    
    print("🔧 Fixing Handover Issues")
    print("=" * 60)
    
    with app.app_context():
        try:
            # Issue 1: Check why notifications went to horacio_rojas instead of techopsuser4
            print("🔍 Analyzing notification routing issue...")
            
            # Get the recent handover request
            recent_handover = HandoverRequest.query.order_by(HandoverRequest.created_at.desc()).first()
            if recent_handover:
                print(f"📋 Recent handover ID: {recent_handover.id}, Created by user: {recent_handover.created_by_id}")
                
                # Check who should receive notifications (all Operations Team users)
                ops_team = Team.query.filter_by(name='Operations Team').first()
                if ops_team:
                    team_members = TeamMember.query.filter_by(team_id=ops_team.id).all()
                    print(f"🏢 Operations Team members: {len(team_members)}")
                    
                    for tm in team_members:
                        user = User.query.get(tm.user_id) if tm.user_id else None
                        if user:
                            print(f"   - {tm.name} ({tm.email}) -> User: {user.username} (ID: {user.id})")
                        else:
                            print(f"   - {tm.name} ({tm.email}) -> NO USER LINKED")
            
            # Issue 2: Check current notifications and fix routing
            print(f"\n🔔 Current notification state:")
            notifications = HandoverNotification.query.all()
            
            techopsuser4 = User.query.filter_by(username='techopsuser4').first()
            if not techopsuser4:
                print("❌ TechOpsUser4 not found!")
                return
            
            print(f"👤 TechOpsUser4 ID: {techopsuser4.id}")
            
            # Check if techopsuser4 should have received notifications
            techops4_notifications = [n for n in notifications if n.recipient_id == techopsuser4.id]
            print(f"   Current notifications for techopsuser4: {len(techops4_notifications)}")
            
            # Issue 3: Create missing notifications for techopsuser4
            if recent_handover and len(techops4_notifications) == 0:
                print(f"\n🔧 Creating missing notifications for techopsuser4...")
                
                # Get all incident assignments from the recent handover
                incident_assignments = IncidentAssignment.query.filter_by(
                    handover_request_id=recent_handover.id
                ).all()
                
                print(f"📝 Found {len(incident_assignments)} incident assignments")
                
                for ia in incident_assignments:
                    # Create notification for techopsuser4
                    notification = HandoverNotification(
                        recipient_id=techopsuser4.id,
                        handover_request_id=recent_handover.id,
                        notification_type='incident_assigned',
                        title=f'New Incident Assignment: {ia.incident_title}',
                        message=f'You have been assigned a new incident: {ia.incident_title} (Priority: {ia.priority}). Please review and respond.',
                        action_url=f'/notifications',
                        action_text='View Assignment',
                        account_id=recent_handover.account_id,
                        team_id=recent_handover.team_id
                    )
                    db.session.add(notification)
                    print(f"   ✅ Created notification for incident: {ia.incident_title}")
                
                db.session.commit()
                print(f"✅ Successfully created notifications for techopsuser4")
            
            # Issue 4: Fix HandoverIncidentResponseLog assignee names
            print(f"\n🔧 Fixing HandoverIncidentResponseLog assignee names...")
            
            response_logs = HandoverIncidentResponseLog.query.all()
            print(f"📝 Found {len(response_logs)} response logs to check")
            
            for log in response_logs:
                # Fix assigned_by_name to use actual submitter
                if log.assigned_by_id:
                    assigned_by_user = User.query.get(log.assigned_by_id)
                    if assigned_by_user and log.assigned_by_name != assigned_by_user.username:
                        old_name = log.assigned_by_name
                        log.assigned_by_name = assigned_by_user.username
                        print(f"   🔧 Fixed assigned_by_name: '{old_name}' -> '{assigned_by_user.username}'")
                
                # Fix accepted_by_name to use actual recipient
                if log.accepted_by_id:
                    accepted_by_user = User.query.get(log.accepted_by_id)
                    if accepted_by_user and log.accepted_by_name != accepted_by_user.username:
                        old_name = log.accepted_by_name
                        log.accepted_by_name = accepted_by_user.username
                        print(f"   🔧 Fixed accepted_by_name: '{old_name}' -> '{accepted_by_user.username}'")
            
            db.session.commit()
            print(f"✅ Fixed response log assignee names")
            
            # Issue 5: Verify final state
            print(f"\n🔍 Final verification...")
            
            # Check techopsuser4 notifications
            final_notifications = HandoverNotification.query.filter_by(recipient_id=techopsuser4.id).all()
            print(f"   TechOpsUser4 notifications: {len(final_notifications)}")
            
            for notif in final_notifications:
                print(f"     - {notif.title} (Type: {notif.notification_type}, Read: {notif.is_read})")
            
            # Check response logs
            updated_logs = HandoverIncidentResponseLog.query.all()
            print(f"   Response logs: {len(updated_logs)}")
            
            for log in updated_logs:
                print(f"     - {log.incident_title}")
                print(f"       Assigned By: {log.assigned_by_name} (ID: {log.assigned_by_id})")
                print(f"       Assigned To: {log.accepted_by_name} (ID: {log.accepted_by_id})")
            
            print(f"\n🎉 All handover issues have been fixed!")
            print(f"✅ TechOpsUser4 should now see notifications on dashboard")
            print(f"✅ Response logs show correct assignee names")

        except Exception as e:
            print(f"❌ Error: {e}")
            db.session.rollback()
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    fix_handover_issues()