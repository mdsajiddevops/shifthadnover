#!/usr/bin/env python3
"""
Check user requests with proper Flask app context
"""
import sys
sys.path.append('/app')

def check_user_requests():
    """Check if techopsuser1 has any requests"""
    
    print("🔍 CHECKING USER REQUESTS")
    print("=" * 60)
    
    try:
        from app import app, db
        
        with app.app_context():
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
                    import traceback
                    traceback.print_exc()
                    
            else:
                print('❌ User techopsuser1 not found')
                
                # List some users to help debug
                all_users = User.query.limit(10).all()
                print(f'Available users: {[u.username for u in all_users]}')
                
    except Exception as e:
        print(f"❌ Error checking user requests: {e}")
        import traceback
        traceback.print_exc()

def check_dashboard_route():
    """Check if the dashboard route passes user_requests properly"""
    
    print(f"\n🔍 CHECKING DASHBOARD ROUTE")
    print("=" * 60)
    
    try:
        with open('/app/routes/shift_swap_leave.py', 'r') as f:
            content = f.read()
        
        if 'user_requests=user_requests' in content:
            print('✅ Dashboard route passes user_requests to template')
        else:
            print('❌ Dashboard route may not be passing user_requests')
            
        # Check if get_user_requests is called
        if 'get_user_requests(current_user.id)' in content:
            print('✅ Dashboard route calls get_user_requests')
        else:
            print('❌ Dashboard route may not be calling get_user_requests')
            
    except Exception as e:
        print(f"❌ Error checking dashboard route: {e}")

if __name__ == "__main__":
    check_user_requests()
    check_dashboard_route()