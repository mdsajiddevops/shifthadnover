#!/usr/bin/env python3
"""
Debug the 500 Internal Server Error in the approval route
"""
import sys
import os

# Add the current directory to Python path
sys.path.append('/app')

def debug_approval_500_error():
    """Debug what's causing the 500 error in approval"""
    
    print("🔍 DEBUGGING 500 INTERNAL SERVER ERROR")
    print("=" * 60)
    
    try:
        from app import app, db
        from models.shift_swap_leave import ShiftSwapRequest
        from services.shift_swap_leave_service import ShiftSwapLeaveService
        
        with app.app_context():
            # Test the exact same approval process that's failing
            print("📋 Testing Request ID 3 approval...")
            
            # Get the request
            request = ShiftSwapRequest.query.get(3)
            if not request:
                print("❌ Request ID 3 not found!")
                return
                
            print(f"✅ Found Request ID 3:")
            print(f"  • Status: {request.status}")
            print(f"  • Requester ID: {request.requester_id}")
            print(f"  • Swap With ID: {request.swap_with_id}")
            print(f"  • Original Date: {request.original_date}")
            print(f"  • Original Shift: {request.original_shift_code}")
            print(f"  • Swap Date: {request.swap_date}")
            print(f"  • Swap Shift: {request.swap_shift_code}")
            
            # Try to approve it step by step to find where it fails
            try:
                print(f"\n🧪 Step 1: Initialize service...")
                service = ShiftSwapLeaveService()
                print("✅ Service initialized")
                
                print(f"\n🧪 Step 2: Check service method exists...")
                if hasattr(service, 'approve_swap_request'):
                    print("✅ approve_swap_request method exists")
                else:
                    print("❌ approve_swap_request method missing!")
                    return
                
                print(f"\n🧪 Step 3: Call approval method...")
                
                # This is the exact call that the route makes
                result = service.approve_swap_request(
                    request_id=3,
                    approver_id=1,  # superadmin user ID
                    comments='Debug test approval'
                )
                
                print(f"✅ Approval method returned: {result}")
                
            except Exception as service_error:
                print(f"❌ Service error: {service_error}")
                import traceback
                print("📋 Full traceback:")
                traceback.print_exc()
                
                # Let's try to see what's in the service file
                print(f"\n🔍 Checking service file...")
                service_file = '/app/services/shift_swap_leave_service.py'
                
                try:
                    with open(service_file, 'r') as f:
                        content = f.read()
                    
                    # Look for the approve_swap_request method
                    if 'def approve_swap_request' in content:
                        lines = content.split('\n')
                        for i, line in enumerate(lines):
                            if 'def approve_swap_request' in line:
                                print(f"\n📋 Found method at line {i+1}:")
                                for j in range(max(0, i), min(len(lines), i+20)):
                                    print(f"  {j+1:3}: {lines[j]}")
                                break
                    else:
                        print("❌ approve_swap_request method not found in service!")
                        
                except Exception as file_error:
                    print(f"❌ Error reading service file: {file_error}")
                
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

def check_route_error_handling():
    """Check if the route has proper error handling"""
    
    print(f"\n🔍 CHECKING ROUTE ERROR HANDLING")
    print("=" * 60)
    
    try:
        route_file = '/app/routes/shift_swap_leave.py'
        
        with open(route_file, 'r') as f:
            content = f.read()
        
        # Find the approval route
        lines = content.split('\n')
        in_approve_function = False
        for i, line in enumerate(lines):
            if 'def approve_swap_request' in line and 'route' in lines[i-1]:
                print(f"📋 Approval Route Function (lines {i+1}-{i+30}):")
                for j in range(max(0, i-2), min(len(lines), i+30)):
                    prefix = ">>> " if j == i else "    "
                    print(f"{prefix}{j+1:3}: {lines[j]}")
                break
                
    except Exception as e:
        print(f"❌ Error checking route: {e}")

def test_service_import():
    """Test if the service can be imported and used"""
    
    print(f"\n🔍 TESTING SERVICE IMPORT")
    print("=" * 60)
    
    try:
        print("📋 Testing service import...")
        from services.shift_swap_leave_service import ShiftSwapLeaveService
        print("✅ Service imported successfully")
        
        service = ShiftSwapLeaveService()
        print("✅ Service instantiated successfully")
        
        # Check what methods are available
        methods = [method for method in dir(service) if not method.startswith('_')]
        print(f"📋 Available methods: {methods}")
        
        # Check if the method signature is correct
        import inspect
        if hasattr(service, 'approve_swap_request'):
            sig = inspect.signature(service.approve_swap_request)
            print(f"📋 Method signature: approve_swap_request{sig}")
        else:
            print("❌ approve_swap_request method not found!")
            
    except Exception as e:
        print(f"❌ Service import error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_approval_500_error()
    check_route_error_handling()
    test_service_import()