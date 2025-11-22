#!/usr/bin/env python3
"""
Fix the request statuses and ensure we have pending requests to test
"""
import sys
import os

# Add the current directory to Python path
sys.path.append('/app')

def check_and_fix_request_statuses():
    """Check all request statuses and reset some to pending"""
    
    print("🔍 CHECKING AND FIXING REQUEST STATUSES")
    print("=" * 60)
    
    try:
        from app import app, db
        from models.shift_swap_leave import ShiftSwapRequest
        
        with app.app_context():
            # Get all requests
            all_requests = ShiftSwapRequest.query.all()
            
            print(f"📋 All Shift Swap Requests:")
            for req in all_requests:
                print(f"  • Request ID {req.id}: Status = {req.status}")
                print(f"    Requester: User {req.requester_id} ↔ User {req.swap_with_id}")
                print(f"    Date: {req.original_date} ({req.original_shift_code} → {req.swap_shift_code})")
                print()
            
            # Count by status
            pending_count = ShiftSwapRequest.query.filter_by(status='pending').count()
            approved_count = ShiftSwapRequest.query.filter_by(status='approved').count()
            
            print(f"📊 Status Summary:")
            print(f"  • Pending: {pending_count}")
            print(f"  • Approved: {approved_count}")
            
            if pending_count == 0:
                print(f"\n🔄 No pending requests! Resetting some to pending for testing...")
                
                # Reset the last 2 approved requests back to pending
                approved_requests = ShiftSwapRequest.query.filter_by(status='approved').limit(2).all()
                
                for req in approved_requests:
                    print(f"🔄 Resetting Request ID {req.id} to pending")
                    req.status = 'pending'
                    req.approved_by_id = None
                    req.approved_at = None
                    req.approval_comments = None
                
                db.session.commit()
                print("✅ Reset requests to pending status")
                
                # Verify the reset
                new_pending_count = ShiftSwapRequest.query.filter_by(status='pending').count()
                print(f"📊 Now have {new_pending_count} pending requests")
                
                # Show the pending requests
                pending_requests = ShiftSwapRequest.query.filter_by(status='pending').all()
                print(f"\n📋 Pending Requests for Testing:")
                for req in pending_requests:
                    print(f"  • Request ID {req.id}: User {req.requester_id} ↔ User {req.swap_with_id}")
            
            else:
                print(f"✅ Have {pending_count} pending requests already")
                
                # Show the pending requests
                pending_requests = ShiftSwapRequest.query.filter_by(status='pending').all()
                print(f"\n📋 Current Pending Requests:")
                for req in pending_requests:
                    print(f"  • Request ID {req.id}: User {req.requester_id} ↔ User {req.swap_with_id}")
                    
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

def test_approval_on_pending_request():
    """Test approval on a confirmed pending request"""
    
    print(f"\n🧪 TESTING APPROVAL ON PENDING REQUEST")
    print("=" * 60)
    
    try:
        from app import app
        
        with app.test_client() as client:
            # Login
            login = client.post('/login', data={'username': 'superadmin', 'password': 'admin123'})
            print(f"🔐 Login status: {login.status_code}")
            
            if login.status_code in [200, 302]:
                # Get a pending request ID
                from models.shift_swap_leave import ShiftSwapRequest
                
                with app.app_context():
                    pending_request = ShiftSwapRequest.query.filter_by(status='pending').first()
                    
                    if pending_request:
                        test_id = pending_request.id
                        print(f"🎯 Testing approval on Request ID {test_id}")
                        
                        # Test the approval
                        approval = client.post(f'/shift-management/admin/approve-swap/{test_id}', 
                                             json={'comments': 'Test approval'})
                        
                        print(f"📊 Approval Status: {approval.status_code}")
                        print(f"📊 Approval Response: {approval.get_data(as_text=True)}")
                        
                        if approval.status_code == 200:
                            print("✅ Approval successful!")
                        else:
                            print(f"❌ Approval failed with status {approval.status_code}")
                            
                    else:
                        print("❌ No pending requests found for testing")
            else:
                print("❌ Login failed")
                
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_and_fix_request_statuses()
    test_approval_on_pending_request()