#!/usr/bin/env python3
"""
Debug and fix the approval endpoint errors
"""
import sys
import os

# Add the current directory to Python path
sys.path.append('/app')

def debug_approval_error():
    """Debug the approval endpoint to find the error"""
    
    print("🔍 DEBUGGING APPROVAL ENDPOINT ERROR")
    print("=" * 60)
    
    try:
        from app import app, db
        from flask import Flask
        from routes.shift_swap_leave import shift_swap_leave_bp
        
        with app.app_context():
            # Check if the approval routes exist
            print("🛣️  Checking approval routes...")
            
            approval_routes = []
            for rule in app.url_map.iter_rules():
                if 'approve' in rule.rule or 'reject' in rule.rule:
                    approval_routes.append(f"{list(rule.methods)} {rule.rule} -> {rule.endpoint}")
            
            if approval_routes:
                print("✅ Found approval routes:")
                for route in approval_routes:
                    print(f"  • {route}")
            else:
                print("❌ No approval routes found!")
            
            # Check the approval methods in the service
            print("\n🔧 Checking approval service methods...")
            
            from services.shift_swap_leave_service import shift_swap_leave_service
            
            # Check if approval methods exist
            service_methods = [method for method in dir(shift_swap_leave_service) if 'approve' in method.lower()]
            
            if service_methods:
                print("✅ Found approval methods in service:")
                for method in service_methods:
                    print(f"  • {method}")
            else:
                print("❌ No approval methods found in service!")
            
            # Test with a sample request
            print("\n🧪 Testing approval workflow...")
            
            from models.shift_swap_leave import ShiftSwapRequest
            from models.models import User
            
            # Get the first pending request
            pending_request = ShiftSwapRequest.query.filter_by(status='pending').first()
            admin_user = User.query.filter_by(role='super_admin').first()
            
            if pending_request and admin_user:
                print(f"✅ Found test data:")
                print(f"  Request ID: {pending_request.id}")
                print(f"  Admin user: {admin_user.username} (ID: {admin_user.id})")
                
                # Try to approve the request
                try:
                    result = shift_swap_leave_service.approve_shift_swap_request(
                        request_id=pending_request.id,
                        approver_id=admin_user.id,
                        comments="Test approval"
                    )
                    
                    if result.get('success'):
                        print("✅ Approval method works correctly")
                        print(f"  Result: {result}")
                        
                        # Rollback the test approval
                        db.session.rollback()
                        
                    else:
                        print(f"❌ Approval method failed: {result.get('error')}")
                        
                except Exception as e:
                    print(f"❌ Error in approval method: {e}")
                    import traceback
                    traceback.print_exc()
                    
            else:
                print("❌ No test data available")
                
    except Exception as e:
        print(f"❌ Debug failed: {e}")
        import traceback
        traceback.print_exc()

def check_routes_file():
    """Check the routes file for any issues"""
    
    print("\n📄 CHECKING ROUTES FILE")
    print("=" * 60)
    
    try:
        with open('/app/routes/shift_swap_leave.py', 'r') as f:
            content = f.read()
            
        # Look for approve-swap route
        if '@shift_swap_leave_bp.route(\'/admin/approve-swap/' in content:
            print("✅ Found approve-swap route definition")
            
            # Extract the route function
            start_idx = content.find('@shift_swap_leave_bp.route(\'/admin/approve-swap/')
            if start_idx != -1:
                # Find the function definition
                func_start = content.find('def ', start_idx)
                if func_start != -1:
                    func_end = content.find('\n@', func_start)
                    if func_end == -1:
                        func_end = content.find('\ndef ', func_start + 10)
                    if func_end == -1:
                        func_end = start_idx + 1000  # fallback
                        
                    route_code = content[start_idx:func_end]
                    print("📋 Approve-swap route code:")
                    print(route_code[:500] + "..." if len(route_code) > 500 else route_code)
                    
        else:
            print("❌ approve-swap route not found!")
            
        # Check for common issues
        if 'current_user' in content and 'from flask_login import' not in content:
            print("⚠️  current_user used but flask_login import might be missing")
            
        if 'jsonify' in content and 'from flask import' in content:
            if 'jsonify' not in content[content.find('from flask import'):content.find('\n', content.find('from flask import'))]:
                print("⚠️  jsonify used but not imported")
                
    except Exception as e:
        print(f"❌ Error checking routes file: {e}")

if __name__ == "__main__":
    debug_approval_error()
    check_routes_file()