#!/usr/bin/env python3
"""
Debug the exact route call that's causing the 500 error
"""
import sys
import os

# Add the current directory to Python path
sys.path.append('/app')

def debug_route_call():
    """Debug the exact route call that's failing"""
    
    print("🔍 DEBUGGING ROUTE CALL")
    print("=" * 60)
    
    try:
        from app import app
        import json
        
        with app.test_client() as client:
            # First login as superadmin
            login_response = client.post('/login', data={
                'username': 'superadmin',
                'password': 'admin123'
            })
            
            print(f"🔐 Login status: {login_response.status_code}")
            
            if login_response.status_code in [200, 302]:  # 302 means redirect after successful login
                print("✅ Login successful")
                
                # Now test the exact approval call that's failing
                print(f"\n🧪 Testing approval route...")
                
                approval_response = client.post('/shift-management/admin/approve-swap/3', 
                                              json={'comments': 'Test approval'},
                                              content_type='application/json')
                
                print(f"📊 Approval Status: {approval_response.status_code}")
                print(f"📊 Approval Response: {approval_response.get_data(as_text=True)}")
                
                if approval_response.status_code == 500:
                    print("❌ 500 Error confirmed - checking server logs...")
                    
                    # Let's try to catch the exact error by modifying the route temporarily
                    print(f"\n🔧 Let's check what parameters the route receives...")
                    
                    # Read the route file to see the exact implementation
                    route_file = '/app/routes/shift_swap_leave.py'
                    
                    with open(route_file, 'r') as f:
                        route_content = f.read()
                    
                    # Find the approval function
                    lines = route_content.split('\n')
                    for i, line in enumerate(lines):
                        if 'def approve_swap_request' in line and not 'service' in line:
                            print(f"\n📋 Route Function Implementation:")
                            for j in range(max(0, i), min(len(lines), i+25)):
                                print(f"  {j+1:3}: {lines[j]}")
                            break
                else:
                    print("✅ Route working now!")
                    
            else:
                print("❌ Login failed")
                
                # Let's try different credentials
                print(f"\n🔧 Trying different login credentials...")
                
                # Try with empty/basic auth
                test_response = client.post('/shift-management/admin/approve-swap/3', 
                                          json={'comments': 'Test without login'})
                
                print(f"📊 No-login test status: {test_response.status_code}")
                print(f"📊 No-login response: {test_response.get_data(as_text=True)}")
                
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

def add_debug_logging_to_route():
    """Add debug logging to the route to see exactly where it fails"""
    
    print(f"\n🔧 ADDING DEBUG LOGGING TO ROUTE")
    print("=" * 60)
    
    try:
        route_file = '/app/routes/shift_swap_leave.py'
        
        with open(route_file, 'r') as f:
            content = f.read()
        
        # Add debug prints to the approval route
        old_function_start = '''def approve_swap_request(request_id):
    """Approve a shift swap request"""
    if current_user.role not in ['super_admin', 'account_admin', 'team_admin']:
        return jsonify({'success': False, 'error': 'Insufficient permissions'}), 403

    try:
        data = request.get_json() if request.is_json else request.form.to_dict()
        comments = data.get('comments', '')

        result = shift_swap_leave_service.approve_swap_request(
            request_id=request_id,
            approver_id=current_user.id,
            comments=comments
        )'''

        new_function_start = '''def approve_swap_request(request_id):
    """Approve a shift swap request"""
    print(f"🚀 ROUTE DEBUG: Starting approval for request_id={request_id}")
    print(f"🚀 ROUTE DEBUG: current_user={current_user}")
    print(f"🚀 ROUTE DEBUG: current_user.role={current_user.role}")
    print(f"🚀 ROUTE DEBUG: current_user.id={current_user.id}")
    
    if current_user.role not in ['super_admin', 'account_admin', 'team_admin']:
        print(f"❌ ROUTE DEBUG: Insufficient permissions")
        return jsonify({'success': False, 'error': 'Insufficient permissions'}), 403

    try:
        print(f"🚀 ROUTE DEBUG: Getting request data...")
        data = request.get_json() if request.is_json else request.form.to_dict()
        print(f"🚀 ROUTE DEBUG: data={data}")
        comments = data.get('comments', '')
        print(f"🚀 ROUTE DEBUG: comments={comments}")

        print(f"🚀 ROUTE DEBUG: Calling service.approve_swap_request...")
        result = shift_swap_leave_service.approve_swap_request(
            request_id=request_id,
            approver_id=current_user.id,
            comments=comments
        )
        print(f"🚀 ROUTE DEBUG: Service returned: {result}")'''

        if old_function_start in content:
            content = content.replace(old_function_start, new_function_start)
            
            with open(route_file, 'w') as f:
                f.write(content)
            
            print("✅ Added debug logging to approval route")
            print("📋 Now the route will print detailed debug info")
            
        else:
            print("⚠️ Could not find exact function pattern to replace")
            print("📋 Let's check what the function actually looks like...")
            
            lines = content.split('\n')
            for i, line in enumerate(lines):
                if 'def approve_swap_request' in line and not 'service' in line:
                    print(f"\n📋 Actual function at line {i+1}:")
                    for j in range(max(0, i), min(len(lines), i+15)):
                        print(f"  {j+1:3}: {lines[j]}")
                    break
            
    except Exception as e:
        print(f"❌ Error adding debug logging: {e}")

if __name__ == "__main__":
    debug_route_call()
    add_debug_logging_to_route()