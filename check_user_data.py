#!/usr/bin/env python3
"""
Check user requests and roster update functionality
"""
import sys
sys.path.append('/app')

def check_user_requests():
    """Check if techopsuser1 has any requests"""
    
    print("🔍 CHECKING USER REQUESTS")
    print("=" * 60)
    
    try:
        from services.shift_swap_leave_service import shift_swap_leave_service
        from models.models import User
        from models.shift_swap_leave import ShiftSwapRequest, LeaveRequest
        
        # Find techopsuser1
        user = User.query.filter_by(username='techopsuser1').first()
        if user:
            print(f'✅ Found user: {user.username} (ID: {user.id})')
            
            # Check direct database queries
            swap_requests = ShiftSwapRequest.query.filter_by(requester_id=user.id).all()
            leave_requests = LeaveRequest.query.filter_by(requester_id=user.id).all()
            
            print(f'📊 Direct DB - Swap requests: {len(swap_requests)}')
            print(f'📊 Direct DB - Leave requests: {len(leave_requests)}')
            
            # Show details
            for req in swap_requests:
                print(f'  • Swap Request ID {req.id}: Status = {req.status}, Created = {req.created_at}')
            
            for req in leave_requests:
                print(f'  • Leave Request ID {req.id}: Status = {req.status}, Created = {req.created_at}')
            
            # Test the service method
            try:
                user_requests = shift_swap_leave_service.get_user_requests(user.id)
                print(f'📊 Service method - Swap requests: {len(user_requests.get("swap_requests", []))}')
                print(f'📊 Service method - Leave requests: {len(user_requests.get("leave_requests", []))}')
            except Exception as e:
                print(f'❌ Service method error: {e}')
                
        else:
            print('❌ User techopsuser1 not found')
            
            # List all users to help debug
            all_users = User.query.all()
            print(f'Available users: {[u.username for u in all_users[:10]]}')
            
    except Exception as e:
        print(f"❌ Error checking user requests: {e}")
        import traceback
        traceback.print_exc()

def check_roster_update_logic():
    """Check if there's roster update logic after approval"""
    
    print(f"\n🔍 CHECKING ROSTER UPDATE LOGIC")
    print("=" * 60)
    
    try:
        # Check if there are roster update methods in the service
        with open('/app/services/shift_swap_leave_service.py', 'r') as f:
            content = f.read()
        
        if 'update_roster' in content or 'roster' in content.lower():
            print('✅ Found roster-related code in service')
        else:
            print('⚠️ No roster update logic found in service')
            
        # Check the approval methods to see if they update roster
        if 'roster' in content.lower() and 'approve' in content:
            print('✅ Approval methods may include roster updates')
        else:
            print('⚠️ Approval methods may not update roster automatically')
            
    except Exception as e:
        print(f"❌ Error checking roster logic: {e}")

if __name__ == "__main__":
    check_user_requests()
    check_roster_update_logic()