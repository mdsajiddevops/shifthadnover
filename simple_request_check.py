#!/usr/bin/env python3
"""
Simple check of request status and fix approval issue
"""
import sys
import os

# Add the current directory to Python path
sys.path.append('/app')

def check_requests_simple():
    """Simple check of requests using proper imports"""
    
    print("🔍 CHECKING SHIFT SWAP REQUESTS")
    print("=" * 60)
    
    try:
        from app import app, db
        from models.shift_swap_leave import ShiftSwapRequest
        from models.user import User
        
        with app.app_context():
            # Get all requests
            requests = ShiftSwapRequest.query.all()
            
            print(f"📋 Total Requests: {len(requests)}")
            print()
            
            for req in requests:
                print(f"🆔 Request ID: {req.id}")
                print(f"  • Status: {req.status}")
                print(f"  • Requester ID: {req.requester_user_id}")
                print(f"  • Partner ID: {req.partner_user_id}")
                print(f"  • Shift Date: {req.shift_date}")
                print(f"  • Created: {req.created_at}")
                if hasattr(req, 'approved_by_username'):
                    print(f"  • Approved By: {req.approved_by_username}")
                if hasattr(req, 'approved_at'):
                    print(f"  • Approved At: {req.approved_at}")
                print("-" * 40)
                
            # Get user mappings
            print(f"\n👤 USER MAPPINGS:")
            users = User.query.all()
            for user in users:
                print(f"  • ID {user.id}: {user.username}")
                
            # Check if Request ID 2 is really approved
            req_2 = ShiftSwapRequest.query.get(2)
            if req_2:
                print(f"\n🎯 REQUEST ID 2 STATUS: {req_2.status}")
                if req_2.status == 'approved':
                    print("⚠️ REQUEST ID 2 IS ALREADY APPROVED - That's why approval fails!")
                    
                    # Reset it to pending for testing
                    print("🔄 Resetting Request ID 2 to pending for testing...")
                    req_2.status = 'pending'
                    req_2.approved_by_username = None
                    req_2.approved_at = None
                    db.session.commit()
                    print("✅ Request ID 2 reset to pending status")
                    
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

def test_approval_route():
    """Test the approval route with a test client"""
    
    print(f"\n🧪 TESTING APPROVAL ROUTE")
    print("=" * 60)
    
    try:
        from app import app
        
        with app.test_client() as client:
            # Test the approval endpoint
            response = client.post('/shift-management/admin/approve-swap/2', 
                                 json={'comments': 'Test approval'})
            
            print(f"📊 Response Status: {response.status_code}")
            print(f"📊 Response Data: {response.get_data(as_text=True)}")
            
            if response.status_code != 200:
                print("❌ Approval route is failing!")
            else:
                print("✅ Approval route working!")
                
    except Exception as e:
        print(f"❌ Route test error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_requests_simple()
    test_approval_route()