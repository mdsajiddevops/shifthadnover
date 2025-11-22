#!/usr/bin/env python3
"""
Check User-TeamMember Links for CTC Account and Supply Chain-L2 Team
"""

import sys
sys.path.append('/app')

from app import app, db
from models.models import User, Team, TeamMember, Account

with app.app_context():
    print("🔍 Checking CTC Account and Supply Chain-L2 Team Links")
    print("=" * 60)
    
    # Find CTC account
    ctc_account = Account.query.filter(Account.name.ilike('%CTC%')).first()
    if not ctc_account:
        print("❌ CTC Account not found")
        # Try other variations
        ctc_account = Account.query.filter(Account.name.ilike('%ctc%')).first()
    
    if ctc_account:
        print(f"🏢 Found CTC Account: {ctc_account.name} (ID: {ctc_account.id})")
    else:
        print("❌ CTC Account not found, showing all accounts:")
        accounts = Account.query.all()
        for acc in accounts:
            print(f"   Account: {acc.name} (ID: {acc.id})")
        print("")
    
    # Find Supply Chain-L2 team
    supply_team = Team.query.filter(Team.name.ilike('%Supply Chain%L2%')).first()
    if not supply_team:
        supply_team = Team.query.filter(Team.name.ilike('%Supply%Chain%')).first()
    
    if supply_team:
        print(f"👥 Found Supply Chain Team: {supply_team.name} (ID: {supply_team.id})")
        print(f"   Team Account ID: {supply_team.account_id}")
    else:
        print("❌ Supply Chain-L2 Team not found, showing all teams:")
        teams = Team.query.all()
        for team in teams:
            print(f"   Team: {team.name} (ID: {team.id}) - Account ID: {team.account_id}")
        print("")
    
    if not ctc_account and not supply_team:
        print("⚠️ Neither CTC account nor Supply Chain-L2 team found. Exiting.")
        exit()
    
    print("\n📊 ANALYSIS RESULTS:")
    print("=" * 60)
    
    # Check TeamMembers in Supply Chain-L2 team
    if supply_team:
        print(f"\n🔍 TeamMembers in {supply_team.name}:")
        print("-" * 40)
        
        team_members = TeamMember.query.filter_by(team_id=supply_team.id).all()
        
        if not team_members:
            print("   No team members found")
        else:
            linked_count = 0
            unlinked_count = 0
            
            for tm in team_members:
                if tm.user_id:
                    user = User.query.get(tm.user_id)
                    linked_count += 1
                    print(f"   ✅ LINKED: {tm.name} (ID: {tm.id}) ↔ User: {user.username if user else 'DELETED'} (ID: {tm.user_id})")
                    if user:
                        print(f"      📧 TeamMember Email: {tm.email}")
                        print(f"      📧 User Email: {user.email}")
                        print(f"      🏢 User Account: {user.account_id}")
                else:
                    unlinked_count += 1
                    print(f"   ❌ UNLINKED: {tm.name} (ID: {tm.id})")
                    print(f"      📧 Email: {tm.email}")
                    print(f"      🏢 Account: {tm.account_id}")
            
            print(f"\n📈 Supply Chain-L2 Team Summary:")
            print(f"   Total TeamMembers: {len(team_members)}")
            print(f"   Linked: {linked_count}")
            print(f"   Unlinked: {unlinked_count}")
    
    # Check Users in CTC account (if found)
    if ctc_account:
        print(f"\n🔍 Users in {ctc_account.name} Account:")
        print("-" * 40)
        
        ctc_users = User.query.filter_by(account_id=ctc_account.id).all()
        
        if not ctc_users:
            print("   No users found in CTC account")
        else:
            linked_count = 0
            unlinked_count = 0
            
            for user in ctc_users:
                # Check if user has a TeamMember link
                team_member = TeamMember.query.filter_by(user_id=user.id).first()
                
                if team_member:
                    linked_count += 1
                    print(f"   ✅ LINKED: User: {user.username} (ID: {user.id}) ↔ TeamMember: {team_member.name} (ID: {team_member.id})")
                    print(f"      📧 User Email: {user.email}")
                    print(f"      📧 TeamMember Email: {team_member.email}")
                    print(f"      👥 Team: {team_member.team.name if team_member.team else 'No Team'}")
                else:
                    unlinked_count += 1
                    print(f"   ❌ UNLINKED: User: {user.username} (ID: {user.id})")
                    print(f"      📧 Email: {user.email}")
                    print(f"      👥 User Team ID: {user.team_id}")
            
            print(f"\n📈 CTC Account Summary:")
            print(f"   Total Users: {len(ctc_users)}")
            print(f"   Linked to TeamMembers: {linked_count}")
            print(f"   Unlinked: {unlinked_count}")
    
    # Cross-reference: Users in Supply Chain-L2 team
    if supply_team:
        print(f"\n🔍 Users assigned to {supply_team.name} (team_id = {supply_team.id}):")
        print("-" * 40)
        
        supply_users = User.query.filter_by(team_id=supply_team.id).all()
        
        if not supply_users:
            print("   No users directly assigned to Supply Chain-L2 team")
        else:
            for user in supply_users:
                team_member = TeamMember.query.filter_by(user_id=user.id).first()
                if team_member:
                    print(f"   ✅ User: {user.username} ↔ TeamMember: {team_member.name}")
                else:
                    print(f"   ⚠️ User: {user.username} (no TeamMember link)")
    
    print(f"\n🎯 POTENTIAL LINKING OPPORTUNITIES:")
    print("-" * 40)
    
    if supply_team:
        # Find unlinked TeamMembers in Supply Chain-L2
        unlinked_tms = TeamMember.query.filter_by(team_id=supply_team.id, user_id=None).all()
        
        # Find unlinked Users (any account for broader matching)
        unlinked_users = User.query.outerjoin(
            TeamMember, User.id == TeamMember.user_id
        ).filter(TeamMember.user_id.is_(None)).all()
        
        if unlinked_tms and unlinked_users:
            print("   Unlinked TeamMembers that could be matched:")
            for tm in unlinked_tms:
                print(f"     TeamMember: {tm.name} ({tm.email})")
                
                # Look for potential user matches
                for user in unlinked_users:
                    if user.email and tm.email:
                        if user.email.lower() == tm.email.lower():
                            print(f"       🎯 PERFECT EMAIL MATCH: User {user.username} ({user.email})")
                        elif user.email.split('@')[0].lower() in tm.email.lower() or tm.email.split('@')[0].lower() in user.email.lower():
                            print(f"       🤔 POTENTIAL MATCH: User {user.username} ({user.email})")
        else:
            print("   No obvious linking opportunities found")
    
    print(f"\n✅ Analysis Complete!")