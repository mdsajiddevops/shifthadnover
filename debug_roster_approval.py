
import sys
sys.path.append('/app')

import os
os.chdir('/app')

from app import app
from models.models import db, User, ShiftRoster, TeamMember
from models.shift_swap_leave import LeaveRequest
from services.shift_swap_leave_service import ShiftSwapLeaveService
from datetime import datetime

def debug_leave_approval():
    """Debug a specific leave request approval"""
    
    with app.app_context():
        print("=== Debugging Leave Request Approval ===")
        
        # Get a specific approved leave request
        leave_request = LeaveRequest.query.filter_by(
            requester_id=40,  # techopsuser1
            status='approved'
        ).first()
        
        if not leave_request:
            print("❌ No approved leave request found")
            return
            
        print(f"✅ Found leave request {leave_request.id}")
        print(f"   Requester ID: {leave_request.requester_id}")
        print(f"   Leave date: {leave_request.leave_date}")
        print(f"   Leave type: {leave_request.leave_type}")
        print(f"   Status: {leave_request.status}")
        
        # Get team member record
        team_member = TeamMember.query.filter_by(user_id=leave_request.requester_id).first()
        if not team_member:
            print("❌ No team member record found")
            return
            
        print(f"✅ Found team member {team_member.id}")
        
        # Check current roster entry
        roster_entry = ShiftRoster.query.filter_by(
            date=leave_request.leave_date,
            team_member_id=team_member.id
        ).first()
        
        if roster_entry:
            print(f"✅ Found roster entry:")
            print(f"   Shift code: {roster_entry.shift_code}")
            print(f"   Date: {roster_entry.date}")
            print(f"   Team member ID: {roster_entry.team_member_id}")
        else:
            print("❌ No roster entry found for this date")
            
        # Test the roster update function manually
        print("\n=== Testing Manual Roster Update ===")
        service = ShiftSwapLeaveService()
        
        # Mock the _execute_leave_roster_update function logic
        try:
            print("Step 1: Getting team member ID...")
            requester_tm_id = team_member.id
            print(f"✅ Team member ID: {requester_tm_id}")
            
            print("Step 2: Finding roster entry...")
            roster_entry = ShiftRoster.query.filter_by(
                date=leave_request.leave_date,
                team_member_id=requester_tm_id,
                account_id=leave_request.account_id
            ).first()
            
            if roster_entry:
                print(f"✅ Found roster entry: {roster_entry.shift_code}")
                print("Step 3: Updating shift code to LE...")
                original_code = roster_entry.shift_code
                roster_entry.shift_code = 'LE'
                db.session.commit()
                print(f"✅ Updated from {original_code} to {roster_entry.shift_code}")
                
                # Verify the update
                updated_entry = ShiftRoster.query.filter_by(
                    date=leave_request.leave_date,
                    team_member_id=requester_tm_id,
                    account_id=leave_request.account_id
                ).first()
                print(f"✅ Verification: {updated_entry.shift_code}")
                
            else:
                print("❌ No roster entry found - creating new one...")
                leave_entry = ShiftRoster(
                    date=leave_request.leave_date,
                    team_member_id=requester_tm_id,
                    shift_code='LE',
                    account_id=leave_request.account_id,
                    team_id=leave_request.team_id
                )
                db.session.add(leave_entry)
                db.session.commit()
                print("✅ Created new leave entry")
                
        except Exception as e:
            print(f"❌ Error during manual update: {str(e)}")
            db.session.rollback()

if __name__ == "__main__":
    debug_leave_approval()
