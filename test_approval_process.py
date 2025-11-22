
import sys
sys.path.append('/app')

import os
os.chdir('/app')

from app import app
from models.models import db, User
from models.shift_swap_leave import LeaveRequest
from services.shift_swap_leave_service import ShiftSwapLeaveService
from datetime import datetime, date

def test_leave_approval_process():
    """Test the complete leave approval process"""
    
    with app.app_context():
        print("=== Testing Leave Approval Process ===")
        
        # Get an admin user (user with ID 1 should be admin)
        admin_user = User.query.filter_by(id=1).first()
        if not admin_user:
            print("❌ No admin user found")
            return
            
        print(f"✅ Found admin user: {admin_user.username}")
        
        # Get a pending leave request (if any)
        pending_leave = LeaveRequest.query.filter_by(status='pending').first()
        
        if not pending_leave:
            print("❌ No pending leave requests found")
            print("Let's check approved requests to understand the pattern...")
            
            approved_leave = LeaveRequest.query.filter_by(status='approved').first()
            if approved_leave:
                print(f"✅ Found approved leave request {approved_leave.id}")
                print(f"   Requester: {approved_leave.requester_id}")
                print(f"   Account: {approved_leave.account_id}")
                print(f"   Team: {approved_leave.team_id}")
                print(f"   Leave date: {approved_leave.leave_date}")
                print(f"   Leave type: {approved_leave.leave_type}")
            return
            
        print(f"✅ Found pending leave request {pending_leave.id}")
        
        # Test the approval service
        service = ShiftSwapLeaveService()
        
        print("\n=== Testing Approval Function ===")
        try:
            result = service.approve_leave_request(
                request_id=pending_leave.id,
                approver_id=admin_user.id,
                comments="Test approval from debug script"
            )
            
            print(f"Approval result: {result}")
            
            if result.get('success'):
                print("✅ Approval succeeded!")
                
                # Check if roster was updated
                from models.models import ShiftRoster, TeamMember
                team_member = TeamMember.query.filter_by(user_id=pending_leave.requester_id).first()
                if team_member:
                    roster_entry = ShiftRoster.query.filter_by(
                        date=pending_leave.leave_date,
                        team_member_id=team_member.id
                    ).first()
                    
                    if roster_entry:
                        print(f"✅ Roster entry found: {roster_entry.shift_code}")
                        if roster_entry.shift_code == 'LE':
                            print("✅ Roster correctly updated to leave code!")
                        else:
                            print(f"❌ Roster shows {roster_entry.shift_code}, expected LE")
                    else:
                        print("❌ No roster entry found")
                else:
                    print("❌ Team member not found")
                    
            else:
                print(f"❌ Approval failed: {result.get('error', 'Unknown error')}")
                
        except Exception as e:
            print(f"❌ Exception during approval: {str(e)}")
            import traceback
            traceback.print_exc()

def test_roster_update_function_directly():
    """Test the roster update function directly"""
    
    with app.app_context():
        print("\n=== Testing Roster Update Function Directly ===")
        
        # Get an approved leave request to test with
        approved_leave = LeaveRequest.query.filter_by(status='approved').first()
        if not approved_leave:
            print("❌ No approved leave requests found")
            return
            
        print(f"✅ Found approved leave request {approved_leave.id}")
        
        service = ShiftSwapLeaveService()
        
        try:
            result = service._execute_leave_roster_update(approved_leave)
            print(f"Roster update result: {result}")
            
            if result.get('success'):
                print("✅ Roster update function succeeded!")
            else:
                print(f"❌ Roster update function failed: {result.get('error', 'Unknown error')}")
                
        except Exception as e:
            print(f"❌ Exception in roster update: {str(e)}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    test_leave_approval_process()
    test_roster_update_function_directly()
