
import sys
sys.path.append('/app')

import os
os.chdir('/app')

from app import app
from models.models import db, User, ShiftRoster, TeamMember
from models.shift_swap_leave import LeaveRequest

def debug_query_filters():
    """Debug the exact query filters causing issues"""
    
    with app.app_context():
        print("=== Debugging Roster Query Filters ===")
        
        # Get a specific approved leave request
        leave_request = LeaveRequest.query.filter_by(
            requester_id=40,  # techopsuser1
            status='approved'
        ).first()
        
        if not leave_request:
            print("❌ No approved leave request found")
            return
            
        print(f"✅ Found leave request {leave_request.id}")
        print(f"   Account ID: {leave_request.account_id}")
        print(f"   Team ID: {leave_request.team_id}")
        print(f"   Leave date: {leave_request.leave_date}")
        
        # Get team member record
        team_member = TeamMember.query.filter_by(user_id=leave_request.requester_id).first()
        if not team_member:
            print("❌ No team member record found")
            return
            
        print(f"✅ Found team member {team_member.id}")
        
        # Test different query combinations
        print("\n=== Testing Query Combinations ===")
        
        # Query 1: Just date and team_member_id (what worked in debug)
        roster1 = ShiftRoster.query.filter_by(
            date=leave_request.leave_date,
            team_member_id=team_member.id
        ).first()
        print(f"Query 1 (date + team_member_id): {'✅ Found' if roster1 else '❌ Not found'}")
        if roster1:
            print(f"   Shift: {roster1.shift_code}, Account: {roster1.account_id}, Team: {roster1.team_id}")
        
        # Query 2: Add account_id (my debug script)  
        roster2 = ShiftRoster.query.filter_by(
            date=leave_request.leave_date,
            team_member_id=team_member.id,
            account_id=leave_request.account_id
        ).first()
        print(f"Query 2 (+ account_id): {'✅ Found' if roster2 else '❌ Not found'}")
        if roster2:
            print(f"   Shift: {roster2.shift_code}, Account: {roster2.account_id}, Team: {roster2.team_id}")
        
        # Query 3: The full service query (with team_id)
        roster3 = ShiftRoster.query.filter_by(
            date=leave_request.leave_date,
            team_member_id=team_member.id,
            account_id=leave_request.account_id,
            team_id=leave_request.team_id
        ).first()
        print(f"Query 3 (+ team_id): {'✅ Found' if roster3 else '❌ Not found'}")
        if roster3:
            print(f"   Shift: {roster3.shift_code}, Account: {roster3.account_id}, Team: {roster3.team_id}")
        
        print(f"\n=== Leave Request Data ===")
        print(f"Expected account_id: {leave_request.account_id}")
        print(f"Expected team_id: {leave_request.team_id}")
        
        if roster1:
            print(f"\n=== Roster Entry Data ===")
            print(f"Actual account_id: {roster1.account_id}")
            print(f"Actual team_id: {roster1.team_id}")
            
            if roster1.account_id != leave_request.account_id:
                print("❌ MISMATCH: account_id doesn't match!")
            if roster1.team_id != leave_request.team_id:
                print("❌ MISMATCH: team_id doesn't match!")

if __name__ == "__main__":
    debug_query_filters()
