#!/usr/bin/env python3
"""
Check if any previously unlinked Supply Chain-L2 team members have now logged in via SSO
and got automatically linked to User accounts.
"""

import sys
import os
sys.path.append('/app')

from app import app, db
from models.models import User, TeamMember, Account, Team
from datetime import datetime

def check_sso_linking_updates():
    """Check current linking status for Supply Chain-L2 team members"""
    
    print("=== SSO Linking Status Check ===")
    print(f"Timestamp: {datetime.now()}")
    print()
    
    # Get Supply Chain-L2 team info
    supply_chain_team = Team.query.filter_by(name='Supply Chain-L2').first()
    if not supply_chain_team:
        print("❌ Supply Chain-L2 team not found!")
        return
    
    print(f"🔍 Analyzing Supply Chain-L2 Team (ID: {supply_chain_team.id})")
    print()
    
    # Get all team members
    team_members = TeamMember.query.filter_by(team_id=supply_chain_team.id).all()
    
    print(f"📊 Total TeamMembers: {len(team_members)}")
    print()
    
    # Previously unlinked users (from our last check)
    previously_unlinked = [
        'pramod.shrivastava@techcorp.com',
        'neeha.palavari@techcorp.com', 
        'prashant.singh@techcorp.com',
        'shahataaz.dudekula@techcorp.com',
        'bharath.nataraja@techcorp.com',
        'sudhanshu.srivastava@techcorp.com',
        'harika.boghra@techcorp.com',
        'santosh.rath@techcorp.com',
        'garima.singh@techcorp.com',
        'atharva.tiwari@techcorp.com',
        'shodha.hm@techcorp.com',
        'swetha.singh@techcorp.com',
        'bramhendra.kumar@techcorp.com',
        'umabharathy.trichy@techcorp.com'
    ]
    
    # Check current status
    linked_count = 0
    unlinked_count = 0
    newly_linked = []
    still_unlinked = []
    
    for tm in team_members:
        if tm.user_id:
            linked_count += 1
            user = User.query.get(tm.user_id)
            if user and user.email.lower() in [email.lower() for email in previously_unlinked]:
                newly_linked.append({
                    'name': tm.name,
                    'email': tm.email,
                    'user_email': user.email,
                    'user_created': user.created_at,
                    'linked_at': 'Recent' if user.created_at else 'Unknown'
                })
        else:
            unlinked_count += 1
            if tm.email and tm.email.lower() in [email.lower() for email in previously_unlinked]:
                still_unlinked.append({
                    'name': tm.name,
                    'email': tm.email,
                    'id': tm.id
                })
    
    # Display results
    print(f"📈 CURRENT STATUS:")
    print(f"   ✅ Linked: {linked_count}")
    print(f"   ❌ Unlinked: {unlinked_count}")
    print(f"   📊 Link Rate: {(linked_count/len(team_members)*100):.1f}%")
    print()
    
    if newly_linked:
        print(f"🎉 NEWLY LINKED USERS ({len(newly_linked)}):")
        print("   Users who have logged in via SSO and got automatically linked:")
        for user in newly_linked:
            print(f"   ✅ {user['name']}")
            print(f"      TeamMember Email: {user['email']}")
            print(f"      User Email: {user['user_email']}")
            print(f"      User Created: {user['user_created']}")
            print()
    else:
        print("📭 No new SSO logins detected from previously unlinked users")
        print()
    
    if still_unlinked:
        print(f"⏳ STILL UNLINKED ({len(still_unlinked)}):")
        print("   Users who haven't logged in via SSO yet:")
        for user in still_unlinked:
            print(f"   ❌ {user['name']} ({user['email']})")
        print()
    
    # Check for any new User accounts created recently
    print("🔍 RECENT USER ACCOUNT ACTIVITY:")
    recent_users = User.query.filter(
        User.created_at >= '2024-11-18'
    ).order_by(User.created_at.desc()).all()
    
    if recent_users:
        print(f"   Found {len(recent_users)} recent User accounts:")
        for user in recent_users:
            print(f"   📅 {user.username} ({user.email}) - Created: {user.created_at}")
    else:
        print("   No recent User accounts found")
    print()
    
    # Summary
    print("=== SUMMARY ===")
    if newly_linked:
        print(f"✅ SUCCESS: {len(newly_linked)} users automatically linked via SSO!")
        print("   The automated linking system is working correctly.")
    else:
        print("⏳ WAITING: No SSO logins detected from unlinked users yet.")
        print("   The system is ready to automatically link them when they log in.")
    
    print(f"📊 Remaining unlinked: {len(still_unlinked)}/14 original unlinked users")

if __name__ == "__main__":
    with app.app_context():
        try:
            check_sso_linking_updates()
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()