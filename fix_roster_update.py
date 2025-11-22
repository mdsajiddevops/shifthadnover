#!/usr/bin/env python3
"""
Fix the roster update issue in shift swap approval
The current approval method is not calling the roster swap execution
"""

def fix_roster_update_issue():
    """Fix the roster update issue by updating the approval method"""
    
    print("=== FIXING ROSTER UPDATE ISSUE ===")
    print()
    
    # Read the current service file
    with open('/app/services/shift_swap_leave_service.py', 'r') as f:
        content = f.read()
    
    # Find the problematic approval method (the one without roster update)
    old_method = '''    def approve_swap_request(self, request_id, approver_id, comments=''):
        """Approve a shift swap request"""
        try:
            from models.shift_swap_leave import ShiftSwapRequest
            from models.models import User
            from app import db
            from datetime import datetime

            request_obj = ShiftSwapRequest.query.get(request_id)
            if not request_obj:
                return {'success': False, 'message': 'Request not found'}

            if request_obj.status != 'pending':
                return {'success': False, 'message': 'Request is not pending'}

            # Get the approver user object
            approver = User.query.get(approver_id)
            if not approver:
                return {'success': False, 'message': 'Approver not found'}

            # Update the request
            request_obj.status = 'approved'
            request_obj.approved_by_id = approver_id  # Use the ID, not the object
            request_obj.approved_at = datetime.utcnow()
            request_obj.admin_comments = comments

            db.session.commit()
            return {'success': True, 'message': 'Request approved successfully'}

        except Exception as e:
            print(f'Error approving swap request: {e}')
            return {'success': False, 'message': str(e)}'''

    # New method with roster update
    new_method = '''    def approve_swap_request(self, request_id, approver_id, comments=''):
        """Approve a shift swap request and update roster"""
        try:
            from models.shift_swap_leave import ShiftSwapRequest
            from models.models import User
            from app import db
            from datetime import datetime

            request_obj = ShiftSwapRequest.query.get(request_id)
            if not request_obj:
                return {'success': False, 'message': 'Request not found'}

            if request_obj.status != 'pending':
                return {'success': False, 'message': 'Request is not pending'}

            # Get the approver user object
            approver = User.query.get(approver_id)
            if not approver:
                return {'success': False, 'message': 'Approver not found'}

            # Update the request
            request_obj.status = 'approved'
            request_obj.approved_by_id = approver_id  # Use the ID, not the object
            request_obj.approved_at = datetime.utcnow()
            request_obj.admin_comments = comments

            # CRITICAL FIX: Execute the roster swap
            print(f"🔄 Executing roster swap for request {request_id}")
            roster_result = self._execute_roster_swap(request_obj)
            if not roster_result['success']:
                print(f"❌ Roster swap failed: {roster_result.get('error', 'Unknown error')}")
                db.session.rollback()
                return {'success': False, 'message': f'Roster update failed: {roster_result.get("error", "Unknown error")}'}
            
            print(f"✅ Roster swap executed successfully for request {request_id}")
            print(f"   - {request_obj.requester.username}: {request_obj.original_shift_code} → {request_obj.swap_shift_code}")
            print(f"   - {request_obj.swap_with.username}: {request_obj.swap_shift_code} → {request_obj.original_shift_code}")

            db.session.commit()
            return {'success': True, 'message': 'Request approved successfully and roster updated'}

        except Exception as e:
            print(f'❌ Error approving swap request: {e}')
            db.session.rollback()
            return {'success': False, 'message': str(e)}'''

    # Replace the method
    if old_method in content:
        updated_content = content.replace(old_method, new_method)
        
        # Write the updated content
        with open('/app/services/shift_swap_leave_service.py', 'w') as f:
            f.write(updated_content)
        
        print("✅ Fixed roster update issue in approval method")
        print("📝 Changes made:")
        print("   - Added _execute_roster_swap() call")
        print("   - Added proper error handling with rollback")
        print("   - Added detailed logging for roster swap execution")
        print("   - Enhanced success message to confirm roster update")
        return True
    else:
        print("❌ Could not find the target approval method to fix")
        return False

if __name__ == "__main__":
    success = fix_roster_update_issue()
    
    if success:
        print("\n🎉 ROSTER UPDATE FIX APPLIED!")
        print("📋 Now when a swap is approved:")
        print("   1. Request status changes to 'approved'")
        print("   2. Roster entries are swapped automatically")
        print("   3. Database changes are committed")
        print("   4. Users see updated shifts in roster")
        print("\n🔄 Please restart the application to apply changes")
    else:
        print("\n❌ FAILED TO APPLY FIX")
        print("Manual intervention may be required")