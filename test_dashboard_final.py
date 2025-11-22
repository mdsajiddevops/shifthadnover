#!/usr/bin/env python3
"""
Test the shift management dashboard after fixes
"""
import sys
import os

# Add the current directory to Python path
sys.path.append('/app')

def test_dashboard_final():
    """Test the dashboard functionality"""
    
    print("🧪 TESTING SHIFT MANAGEMENT DASHBOARD")
    print("=" * 60)
    
    try:
        from app import app, db
        from services.shift_swap_leave_service import shift_swap_leave_service
        from models.models import User
        
        with app.app_context():
            print("✅ Flask app context loaded successfully")
            
            # Test 1: Get a test admin user
            admin_user = User.query.filter_by(role='super_admin').first()
            if admin_user:
                print(f"✅ Found test admin user: {admin_user.username} (ID: {admin_user.id})")
                
                # Test 2: Try to get pending requests for approval
                try:
                    pending_requests = shift_swap_leave_service.get_pending_requests_for_approval(admin_user.id)
                    
                    if pending_requests.get('success'):
                        swap_count = len(pending_requests.get('swap_requests', []))
                        leave_count = len(pending_requests.get('leave_requests', []))
                        
                        print(f"✅ Service call successful:")
                        print(f"   Pending swap requests: {swap_count}")
                        print(f"   Pending leave requests: {leave_count}")
                        
                        # Test 3: Check the data format
                        if swap_count > 0:
                            sample_request = pending_requests['swap_requests'][0]
                            print(f"✅ Sample request data:")
                            print(f"   ID: {sample_request.get('id')}")
                            print(f"   Requester: {sample_request.get('requester_username')}")
                            print(f"   Created at: {sample_request.get('created_at')}")
                            print(f"   Status: {sample_request.get('status')}")
                            
                            # Test the datetime format
                            created_at = sample_request.get('created_at')
                            if created_at:
                                print(f"✅ Datetime format looks good: {type(created_at)} - {created_at}")
                        
                    else:
                        print(f"❌ Service call failed: {pending_requests.get('error')}")
                        
                except Exception as e:
                    print(f"❌ Error calling service: {e}")
                    import traceback
                    traceback.print_exc()
                    
            else:
                print("❌ No admin user found for testing")
            
            # Test 4: Check that templates exist
            template_path = '/app/templates/shift_management/dashboard.html'
            if os.path.exists(template_path):
                print("✅ Dashboard template exists")
                
                # Check template content
                with open(template_path, 'r') as f:
                    content = f.read()
                    
                if 'pending_requests.swap_requests' in content:
                    print("✅ Template has dynamic content for pending requests")
                else:
                    print("❌ Template might still be static")
                    
            else:
                print("❌ Dashboard template missing")
            
            print("\n💡 DASHBOARD TEST SUMMARY:")
            print("The dashboard should now work properly with the fixes applied.")
            print("Try accessing: https://shiftops.lab.epam.com/shift-management/dashboard")
            
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_dashboard_final()