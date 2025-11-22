
import sys
sys.path.append('/app')

import os
os.chdir('/app')

from app import app
from models.models import db, User, ShiftRoster, TeamMember
from models.shift_swap_leave import ShiftSwapRequest, LeaveRequest
from datetime import datetime, date

def check_approved_requests_roster():
    """Check if approved requests have corresponding roster updates"""
    
    with app.app_context():
        print("=== Checking Approved Requests and Roster Updates ===")
        
        # Get techopsuser1's approved swap requests
        user = User.query.filter_by(username='techopsuser1').first()
        if not user:
            print("❌ User techopsuser1 not found")
            return
            
        print(f"✅ Found user: {user.username} (ID: {user.id})")
        
        # Get approved swap requests
        approved_swaps = ShiftSwapRequest.query.filter_by(
            requester_id=user.id,
            status='approved'
        ).all()
        
        print(f"📊 Found {len(approved_swaps)} approved swap requests")
        
        for swap in approved_swaps:
            print(f"\n🔄 Swap Request {swap.id}:")
            print(f"   Original date: {swap.original_date}")
            print(f"   Swap date: {swap.swap_date}")
            print(f"   Status: {swap.status}")
            print(f"   Approved at: {swap.approved_at}")
            
            # Check roster entries for these dates
            # Get team member ID for user
            team_member = TeamMember.query.filter_by(user_id=user.id).first()
            if team_member:
                print(f"   Team member ID: {team_member.id}")
                
                # Check roster for original date
                original_roster = ShiftRoster.query.filter_by(
                    date=swap.original_date,
                    team_member_id=team_member.id
                ).first()
                
                # Check roster for swap date  
                swap_roster = ShiftRoster.query.filter_by(
                    date=swap.swap_date,
                    team_member_id=team_member.id
                ).first()
                
                print(f"   Original date roster: {original_roster.shift_code if original_roster else 'None'}")
                print(f"   Swap date roster: {swap_roster.shift_code if swap_roster else 'None'}")
            else:
                print("   ❌ No team member record found")
        
        # Get approved leave requests
        approved_leaves = LeaveRequest.query.filter_by(
            requester_id=user.id,
            status='approved'
        ).all()
        
        print(f"\n📊 Found {len(approved_leaves)} approved leave requests")
        
        for leave in approved_leaves:
            print(f"\n🏖️ Leave Request {leave.id}:")
            print(f"   Leave date: {leave.leave_date}")
            print(f"   Leave type: {leave.leave_type}")
            print(f"   Status: {leave.status}")
            print(f"   Approved at: {leave.approved_at}")
            
            # Check roster entry for leave date
            team_member = TeamMember.query.filter_by(user_id=user.id).first()
            if team_member:
                leave_roster = ShiftRoster.query.filter_by(
                    date=leave.leave_date,
                    team_member_id=team_member.id
                ).first()
                
                print(f"   Leave date roster: {leave_roster.shift_code if leave_roster else 'None'}")
                expected = 'LE' if leave.leave_type == 'sick' else 'VL' if leave.leave_type == 'vacation' else 'LE'
                if leave_roster and leave_roster.shift_code in ['LE', 'VL', 'HL']:
                    print(f"   ✅ Roster correctly shows leave code: {leave_roster.shift_code}")
                else:
                    print(f"   ❌ Expected leave code, but found: {leave_roster.shift_code if leave_roster else 'None'}")
            else:
                print("   ❌ No team member record found")

if __name__ == "__main__":
    check_approved_requests_roster()
