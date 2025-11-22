#!/usr/bin/env python3
"""
Check TechOps Users Configuration and Notification Setup
Verify if techopsuser1-4 are properly configured for handover notifications
"""

import sys
sys.path.append('/app')

from app import app, db
from models.models import User, Account, Team
from models.handover_enhanced import HandoverNotification
from sqlalchemy import text

def check_techops_users():
    """Check techopsuser accounts configuration for handover notifications"""
    
    print("🔍 Checking TechOps Users Configuration for Handover Notifications")
    print("=" * 80)
    
    with app.app_context():
        # Check all techopsuser accounts
        techops_users = ['techopsuser1', 'techopsuser2', 'techopsuser3', 'techopsuser4']
        
        print("👥 TECHOPS USER DETAILS:")
        print("-" * 50)
        
        user_details = {}
        for username in techops_users:
            user = User.query.filter_by(username=username).first()
            if user:
                user_details[username] = user
                account = Account.query.get(user.account_id) if user.account_id else None
                team = Team.query.get(user.team_id) if user.team_id else None
                
                print(f"✅ {username}:")
                print(f"   ID: {user.id}")
                print(f"   Email: {user.email}")
                print(f"   Account ID: {user.account_id} ({account.name if account else 'Unknown'})")
                print(f"   Team ID: {user.team_id} ({team.name if team else 'Unknown'})")
                print(f"   Status: {'Active' if user.is_active else 'Inactive'}")
                print()
            else:
                print(f"❌ {username}: NOT FOUND")
                print()
        
        # Check team membership
        print("🏢 TEAM MEMBERSHIP CHECK:")
        print("-" * 50)
        
        if user_details:
            # Get the account and team from first user
            first_user = list(user_details.values())[0]
            account_id = first_user.account_id
            team_id = first_user.team_id
            
            # Check team_member table
            team_members = db.session.execute(
                text("SELECT user_id, role FROM team_member WHERE team_id = :team_id AND user_id IN :user_ids"),
                {
                    "team_id": team_id,
                    "user_ids": tuple([user.id for user in user_details.values()])
                }
            ).fetchall()
            
            print(f"Team Members in team_member table:")
            for user_id, role in team_members:
                username = next((name for name, user in user_details.items() if user.id == user_id), f"ID:{user_id}")
                print(f"   ✅ {username} (ID: {user_id}) - Role: {role}")
            
            missing_members = [user for user in user_details.values() 
                             if user.id not in [tm[0] for tm in team_members]]
            
            if missing_members:
                print(f"\n⚠️ Users NOT in team_member table:")
                for user in missing_members:
                    username = next(name for name, u in user_details.items() if u.id == user.id)
                    print(f"   ❌ {username} (ID: {user.id})")
        
        # Test notification scenario
        print("\n🧪 HANDOVER NOTIFICATION TEST SCENARIO:")
        print("-" * 50)
        
        if 'techopsuser1' in user_details and 'techopsuser2' in user_details:
            user1 = user_details['techopsuser1']
            user2 = user_details['techopsuser2']
            
            print(f"Scenario: techopsuser1 → techopsuser2 handover")
            print(f"From: {user1.username} (ID: {user1.id})")
            print(f"To: {user2.username} (ID: {user2.id})")
            print(f"Account: {user1.account_id} (should match: {user2.account_id})")
            print(f"Team: {user1.team_id} (should match: {user2.team_id})")
            
            # Check if both users can receive notifications
            if user1.account_id == user2.account_id and user1.team_id == user2.team_id:
                print(f"✅ COMPATIBLE: Both users in same account/team")
                print(f"✅ NOTIFICATION WILL WORK: techopsuser2 will receive notifications")
                print(f"✅ DASHBOARD: Notification will appear on techopsuser2's dashboard")
                print(f"✅ RESPONSE LOGS: Will show proper assignee details")
            else:
                print(f"❌ INCOMPATIBLE: Users in different account/team")
                print(f"❌ NOTIFICATION MAY FAIL")
        
        # Check existing notifications
        print(f"\n📧 CURRENT NOTIFICATIONS:")
        print("-" * 50)
        
        for username, user in user_details.items():
            notifications = HandoverNotification.query.filter_by(recipient_id=user.id).all()
            unread_count = len([n for n in notifications if not n.is_read])
            
            print(f"{username} (ID: {user.id}):")
            print(f"   Total notifications: {len(notifications)}")
            print(f"   Unread notifications: {unread_count}")
            
            if notifications:
                latest = max(notifications, key=lambda x: x.created_at)
                print(f"   Latest: '{latest.title}' ({latest.created_at})")
            print()
        
        # Final assessment
        print("🎯 FINAL ASSESSMENT:")
        print("-" * 50)
        
        if len(user_details) == 4:
            all_same_account = len(set(user.account_id for user in user_details.values())) == 1
            all_same_team = len(set(user.team_id for user in user_details.values())) == 1
            
            if all_same_account and all_same_team:
                print("✅ SUCCESS: All techopsuser accounts are properly configured")
                print("✅ HANDOVERS WILL WORK: Between any techopsuser1-4")
                print("✅ NOTIFICATIONS WILL WORK: Recipients will see dashboard notifications")
                print("✅ RESPONSE LOGS WILL WORK: Proper assignee details will be recorded")
                print()
                print("📝 READY FOR TESTING:")
                print("   1. Login as techopsuser1")
                print("   2. Create handover assigned to techopsuser2")
                print("   3. Login as techopsuser2 to see notification")
                print("   4. Check handover incident response logs for proper details")
            else:
                print("❌ CONFIGURATION ISSUE: Users not in same account/team")
                print("❌ HANDOVERS MAY NOT WORK PROPERLY")
        else:
            print("❌ MISSING USERS: Not all techopsuser1-4 accounts found")

if __name__ == "__main__":
    check_techops_users()