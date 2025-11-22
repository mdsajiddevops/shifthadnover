#!/usr/bin/env python3
"""
Debug script to investigate the shift API issue
"""
import sys
import os
sys.path.append('/app')

try:
    # Initialize Flask app context
    from app import app, db
    from models.user import User
    from models.team_member import TeamMember
    from models.shift_roster import ShiftRoster
    from datetime import datetime
    
    with app.app_context():
        print("=== DEBUG: Shift API Issue Investigation ===")
        
        # Find techopsuser1
        user = User.query.filter_by(username='techopsuser1').first()
        if not user:
            print("❌ User 'techopsuser1' not found!")
            exit(1)
        
        print(f"✅ Found user: {user.username} (ID: {user.id}, Account ID: {user.account_id})")
        
        # Find team member record
        team_member = TeamMember.query.filter_by(user_id=user.id).first()
        if not team_member:
            print("❌ TeamMember record not found!")
            exit(1)
        
        print(f"✅ Found team member: ID {team_member.id}, Team: {team_member.team_id}")
        
        # Test the date 2025-11-28
        test_date = datetime.strptime("2025-11-28", "%Y-%m-%d").date()
        print(f"✅ Testing date: {test_date}")
        
        # Try the first query (without account_id)
        print("\n--- Query 1: Without account_id ---")
        roster_entry = ShiftRoster.query.filter_by(
            date=test_date,
            team_member_id=team_member.id
        ).first()
        
        if roster_entry:
            print(f"✅ Found roster entry: Shift={roster_entry.shift}, Account ID={roster_entry.account_id}")
        else:
            print("❌ No roster entry found with query 1")
        
        # Try the second query (with account_id)
        print("\n--- Query 2: With account_id ---")
        if user.account_id:
            roster_entry2 = ShiftRoster.query.filter_by(
                date=test_date,
                team_member_id=team_member.id,
                account_id=user.account_id
            ).first()
            
            if roster_entry2:
                print(f"✅ Found roster entry: Shift={roster_entry2.shift}, Account ID={roster_entry2.account_id}")
            else:
                print("❌ No roster entry found with query 2")
        else:
            print("ℹ️ User has no account_id, skipping query 2")
        
        # Show all roster entries for this team member around this date
        print("\n--- All roster entries for this team member (recent) ---")
        all_entries = ShiftRoster.query.filter_by(team_member_id=team_member.id).order_by(ShiftRoster.date.desc()).limit(10).all()
        for entry in all_entries:
            print(f"Date: {entry.date}, Shift: {entry.shift}, Account ID: {entry.account_id}")
        
        # Show all team members for comparison
        print("\n--- All team members ---")
        all_team_members = TeamMember.query.all()[:5]  # Limit to first 5 for readability
        for tm in all_team_members:
            user_obj = User.query.get(tm.user_id)
            if user_obj:
                print(f"Team Member ID: {tm.id}, User: {user_obj.username}, User ID: {tm.user_id}, Team: {tm.team_id}")
        
        print("\n=== Debug Complete ===")
    
except Exception as e:
    print(f"❌ Error during debug: {str(e)}")
    import traceback
    traceback.print_exc()