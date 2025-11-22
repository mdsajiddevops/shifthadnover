
import sys
sys.path.append('/app')

import os
os.chdir('/app')

from app import app
from models.models import db, User, ShiftRoster, TeamMember
from models.shift_swap_leave import LeaveRequest
from datetime import datetime, date

def reset_roster_entries():
    """Reset roster entries to original shift codes"""
    
    with app.app_context():
        print("=== Resetting Roster Entries ===")
        
        # Find the roster entries that were changed to LE
        le_entries = ShiftRoster.query.filter(
            ShiftRoster.shift_code == 'LE'
        ).all()
        
        print(f"Found {len(le_entries)} roster entries with LE code")
        
        for entry in le_entries:
            print(f"Resetting entry: Date {entry.date}, Team Member {entry.team_member_id}")
            # Change back to D (Day shift - common shift code)
            entry.shift_code = 'D'
        
        db.session.commit()
        print("✅ Reset completed")
        
        # Now test the approval of an existing approved leave request
        print("\n=== Testing Roster Update on Approved Request ===")
        
        approved_leave = LeaveRequest.query.filter_by(status='approved').first()
        if approved_leave:
            print(f"Testing with leave request {approved_leave.id}")
            
            # Get the team member
            team_member = TeamMember.query.filter_by(user_id=approved_leave.requester_id).first()
            if team_member:
                # Check current roster
                roster_before = ShiftRoster.query.filter_by(
                    date=approved_leave.leave_date,
                    team_member_id=team_member.id
                ).first()
                
                print(f"Roster before update: {roster_before.shift_code if roster_before else 'None'}")
                
                # Now test the roster update function
                from services.shift_swap_leave_service import ShiftSwapLeaveService
                service = ShiftSwapLeaveService()
                
                result = service._execute_leave_roster_update(approved_leave)
                print(f"Roster update result: {result}")
                
                if result.get('success'):
                    db.session.commit()
                    
                    # Check roster after update
                    roster_after = ShiftRoster.query.filter_by(
                        date=approved_leave.leave_date,
                        team_member_id=team_member.id
                    ).first()
                    
                    print(f"Roster after update: {roster_after.shift_code if roster_after else 'None'}")
                    
                    if roster_after and roster_after.shift_code == 'LE':
                        print("✅ Roster update is working correctly!")
                    else:
                        print("❌ Roster update didn't work as expected")
                else:
                    print(f"❌ Roster update failed: {result.get('error')}")
            else:
                print("❌ Team member not found")
        else:
            print("❌ No approved leave requests found")

if __name__ == "__main__":
    reset_roster_entries()
