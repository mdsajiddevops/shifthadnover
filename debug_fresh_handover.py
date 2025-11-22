#!/usr/bin/env python3
"""
Debug script to check the current handover and notification state after fresh submission
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app, db
from models.models import User, Team, TeamMember
from models.handover_enhanced import HandoverRequest, HandoverNotification, IncidentAssignment, HandoverIncidentResponseLog
from sqlalchemy import text

def debug_fresh_handover_state():
    """Debug the current state after fresh handover submission"""
    
    print("🔍 Debugging Fresh Handover State")
    print("=" * 60)
    
    with app.app_context():
        try:
            # Check recent handover requests
            recent_handovers = HandoverRequest.query.order_by(HandoverRequest.created_at.desc()).limit(5).all()
            print(f"📋 Recent HandoverRequests: {len(recent_handovers)}")
            
            for hr in recent_handovers:
                print(f"   ID: {hr.id}, Team: {hr.team_id}, Created: {hr.created_at}")
                print(f"   Created By: {hr.created_by_id}")
            
            # Check notifications
            recent_notifications = HandoverNotification.query.order_by(HandoverNotification.created_at.desc()).limit(10).all()
            print(f"\n🔔 Recent HandoverNotifications: {len(recent_notifications)}")
            
            for hn in recent_notifications:
                recipient = User.query.get(hn.recipient_id) if hn.recipient_id else None
                print(f"   ID: {hn.id}, Recipient: {recipient.username if recipient else 'Unknown'} ({hn.recipient_id})")
                print(f"   Title: {hn.title}, Read: {hn.is_read}, Type: {hn.notification_type}, Created: {hn.created_at}")
            
            # Check techopsuser4 specifically
            techopsuser4 = User.query.filter_by(username='techopsuser4').first()
            if techopsuser4:
                print(f"\n👤 TechOpsUser4 Details:")
                print(f"   ID: {techopsuser4.id}, Email: {techopsuser4.email}")
                
                # Check their notifications
                user4_notifications = HandoverNotification.query.filter_by(recipient_id=techopsuser4.id).all()
                print(f"   Notifications: {len(user4_notifications)}")
                
                for notif in user4_notifications:
                    print(f"     - {notif.title} (Type: {notif.notification_type}, Read: {notif.is_read}, Created: {notif.created_at})")
                
                # Check their team membership
                team_memberships = TeamMember.query.filter_by(user_id=techopsuser4.id).all()
                print(f"   Team Memberships: {len(team_memberships)}")
                for tm in team_memberships:
                    team = Team.query.get(tm.team_id)
                    print(f"     - Team: {team.name if team else 'Unknown'} (ID: {tm.team_id})")
            else:
                print("\n❌ TechOpsUser4 not found!")
            
            # Check incident assignments
            recent_assignments = IncidentAssignment.query.limit(5).all()
            print(f"\n🎯 Recent IncidentAssignments: {len(recent_assignments)}")
            
            for ia in recent_assignments:
                assigned_to = User.query.get(ia.assigned_to_id) if ia.assigned_to_id else None
                print(f"   ID: {ia.id}, Assigned To: {assigned_to.username if assigned_to else 'Unknown'} ({ia.assigned_to_id})")
                print(f"   Incident: {ia.incident_title}, Priority: {ia.priority}")
            
            # Check handover incident response logs
            recent_logs = HandoverIncidentResponseLog.query.order_by(HandoverIncidentResponseLog.created_at.desc()).limit(5).all()
            print(f"\n📝 Recent HandoverIncidentResponseLogs: {len(recent_logs)}")
            
            for log in recent_logs:
                assigned_by = User.query.get(log.assigned_by_user_id) if log.assigned_by_user_id else None
                assigned_to = User.query.get(log.assigned_to_user_id) if log.assigned_to_user_id else None
                print(f"   ID: {log.id}, Incident: {log.incident_title}")
                print(f"   Assigned By: {assigned_by.username if assigned_by else 'Unknown'} ({log.assigned_by_user_id})")
                print(f"   Assigned To: {assigned_to.username if assigned_to else 'Unknown'} ({log.assigned_to_user_id})")
                print(f"   From Shift: {log.from_shift}, To Shift: {log.to_shift}")
            
            # Check Operations Team
            ops_team = Team.query.filter_by(name='Operations Team').first()
            if ops_team:
                print(f"\n🏢 Operations Team (ID: {ops_team.id}):")
                team_members = TeamMember.query.filter_by(team_id=ops_team.id).all()
                print(f"   Members: {len(team_members)}")
                
                for tm in team_members:
                    user = User.query.get(tm.user_id) if tm.user_id else None
                    print(f"     - {tm.name} ({tm.email}) -> User: {user.username if user else 'Not Linked'}")

        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    debug_fresh_handover_state()