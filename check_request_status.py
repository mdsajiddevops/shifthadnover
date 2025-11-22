#!/usr/bin/env python3
"""
Check current status of all shift swap requests and fix UI refresh
"""
import sys
import os

# Add the current directory to Python path
sys.path.append('/app')

def check_request_status():
    """Check the current status of all shift swap requests"""
    
    print("📊 CHECKING CURRENT STATUS OF ALL SHIFT SWAP REQUESTS")
    print("=" * 70)
    
    try:
        from app import app, db
        from models.shift_swap_leave import ShiftSwapRequest
        from models.models import User
        
        with app.app_context():
            # Get all shift swap requests
            all_requests = ShiftSwapRequest.query.order_by(ShiftSwapRequest.created_at.desc()).all()
            
            if all_requests:
                print(f"📋 Found {len(all_requests)} total shift swap requests:")
                
                for req in all_requests:
                    requester = User.query.get(req.requester_id) if req.requester_id else None
                    swap_with = User.query.get(req.swap_with_id) if req.swap_with_id else None
                    approved_by = User.query.get(req.approved_by_id) if req.approved_by_id else None
                    
                    print(f"\n  🔄 Request ID: {req.id}")
                    print(f"     Status: {req.status}")
                    print(f"     Requester: {requester.username if requester else 'Unknown'}")
                    print(f"     Swap with: {swap_with.username if swap_with else 'Unknown'}")
                    print(f"     Original: {req.original_date} ({req.original_shift_code})")
                    print(f"     Swap: {req.swap_date} ({req.swap_shift_code})")
                    print(f"     Created: {req.created_at}")
                    if req.approved_by_id:
                        print(f"     Approved by: {approved_by.username if approved_by else 'Unknown'} at {req.approved_at}")
                        print(f"     Comments: {req.approval_comments or 'None'}")
                
                # Count by status
                pending_count = len([r for r in all_requests if r.status == 'pending'])
                approved_count = len([r for r in all_requests if r.status == 'approved'])
                rejected_count = len([r for r in all_requests if r.status == 'rejected'])
                
                print(f"\n📊 STATUS SUMMARY:")
                print(f"  ⏳ Pending: {pending_count}")
                print(f"  ✅ Approved: {approved_count}")
                print(f"  ❌ Rejected: {rejected_count}")
                
                if pending_count == 0:
                    print("\n💡 FINDING: No pending requests remain!")
                    print("   This means the approval process has been working.")
                    print("   The error message might be due to UI not refreshing after successful approval.")
                
            else:
                print("❌ No shift swap requests found")
                
            # Check if there are any notifications that weren't marked as read
            print(f"\n📧 CHECKING NOTIFICATIONS...")
            
            from models.shift_swap_leave import SwapLeaveNotification
            unread_notifications = SwapLeaveNotification.query.filter_by(is_read=False).all()
            
            print(f"   Unread notifications: {len(unread_notifications)}")
            
            if unread_notifications:
                for notif in unread_notifications[:5]:  # Show first 5
                    recipient = User.query.get(notif.recipient_id) if notif.recipient_id else None
                    print(f"   📤 To: {recipient.username if recipient else 'Unknown'} - {notif.notification_type}")
                    
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

def fix_ui_refresh_issue():
    """Fix the UI refresh issue by ensuring proper status updates"""
    
    print(f"\n🔧 FIXING UI REFRESH ISSUE")
    print("=" * 70)
    
    # Update the JavaScript in the template to handle success properly
    template_path = '/app/templates/shift_management/dashboard.html'
    
    try:
        with open(template_path, 'r') as f:
            content = f.read()
        
        # Update the success handling in JavaScript
        old_success_handler = "alert('Swap request approved successfully!');\n                location.reload();"
        new_success_handler = "alert('Swap request approved successfully!');\n                setTimeout(() => { location.reload(true); }, 1000);"
        
        content = content.replace(old_success_handler, new_success_handler)
        
        # Also update error handling
        old_error_handler = "alert('Error: ' + data.error);"
        new_error_handler = "alert('Error: ' + data.error);\n                console.log('Approval error details:', data);"
        
        content = content.replace(old_error_handler, new_error_handler)
        
        # Update the reject success handler too
        old_reject_handler = "alert('Swap request rejected successfully!');\n                location.reload();"
        new_reject_handler = "alert('Swap request rejected successfully!');\n                setTimeout(() => { location.reload(true); }, 1000);"
        
        content = content.replace(old_reject_handler, new_reject_handler)
        
        with open(template_path, 'w') as f:
            f.write(content)
        
        print("✅ Updated JavaScript to handle approval responses better")
        print("  • Added delay before page reload")
        print("  • Added console logging for debugging") 
        print("  • Force refresh with cache bypass")
        
    except Exception as e:
        print(f"❌ Error updating template: {e}")

if __name__ == "__main__":
    check_request_status()
    fix_ui_refresh_issue()