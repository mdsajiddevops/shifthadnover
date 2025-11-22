#!/usr/bin/env python3
"""
Add get_user_requests method to shift swap leave service
"""
import sys
import os

# Add the current directory to Python path
sys.path.append('/app')

def add_get_user_requests_method():
    """Add the get_user_requests method to the service"""
    
    print("🔧 ADDING GET_USER_REQUESTS METHOD TO SERVICE")
    print("=" * 60)
    
    try:
        service_file = '/app/services/shift_swap_leave_service.py'
        
        with open(service_file, 'r') as f:
            content = f.read()
        
        # Check if method already exists
        if 'def get_user_requests(' in content:
            print("✅ get_user_requests method already exists")
            return
        
        # Method to add
        method_code = '''
    def get_user_requests(self, user_id):
        """Get all requests (swap and leave) for a specific user"""
        try:
            from models.shift_swap_leave import ShiftSwapRequest, LeaveRequest
            
            # Get swap requests
            swap_requests = ShiftSwapRequest.query.filter_by(requester_id=user_id).order_by(ShiftSwapRequest.created_at.desc()).all()
            
            # Get leave requests  
            leave_requests = LeaveRequest.query.filter_by(requester_id=user_id).order_by(LeaveRequest.created_at.desc()).all()
            
            return {
                'swap_requests': swap_requests,
                'leave_requests': leave_requests
            }
            
        except Exception as e:
            print(f'Error getting user requests: {e}')
            return {'swap_requests': [], 'leave_requests': []}
'''
        
        # Find the end of the class to add the method
        lines = content.split('\n')
        
        # Find the class and add method before the last line of the file
        class_found = False
        insert_position = len(lines) - 1
        
        for i, line in enumerate(lines):
            if 'class ShiftSwapLeaveService' in line:
                class_found = True
            elif class_found and line.strip() and not line.startswith(' ') and not line.startswith('\t'):
                # We've left the class
                insert_position = i
                break
        
        if class_found:
            # Insert the method
            method_lines = method_code.strip().split('\n')
            for j, method_line in enumerate(method_lines):
                lines.insert(insert_position + j, method_line)
            
            # Write back to file
            with open(service_file, 'w') as f:
                f.write('\n'.join(lines))
            
            print("✅ Added get_user_requests method to service")
            print("  • Fetches user's swap requests")
            print("  • Fetches user's leave requests") 
            print("  • Returns structured data for template")
        else:
            print("❌ Could not find ShiftSwapLeaveService class")
            
    except Exception as e:
        print(f"❌ Error adding method: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    add_get_user_requests_method()