#!/usr/bin/env python3
"""
Diagnose the exact issue with shift swap approval filtering
"""
import sys
import os

# Add the current directory to Python path
sys.path.append('/app')

def diagnose_approval_filtering():
    """Diagnose why admins can't see pending requests"""
    try:
        from app import app, db
        from sqlalchemy import text
        from models.shift_swap_leave import ShiftSwapRequest
        from models.models import User
        
        with app.app_context():
            print("🔍 DIAGNOSING SHIFT SWAP APPROVAL FILTERING ISSUE")
            print("=" * 70)
            
            # 1. Get the pending requests
            print("\n📋 PENDING SHIFT SWAP REQUESTS:")
            pending_requests = ShiftSwapRequest.query.filter_by(status='pending').all()
            
            for req in pending_requests:
                print(f"  • Request ID: {req.id}")
                print(f"    Requester: User ID {req.requester_id} (account_id: {req.account_id}, team_id: {req.team_id})")
                print(f"    Swap Partner: User ID {req.swap_with_id}")
                print(f"    Status: {req.status}")
                print(f"    Created: {req.created_at}")
                print()
            
            # 2. Get admin users and their account/team associations
            print("👥 ADMIN USERS AND THEIR PERMISSIONS:")
            admin_users = User.query.filter(
                User.role.in_(['super_admin', 'account_admin', 'team_admin'])
            ).all()
            
            for admin in admin_users:
                print(f"  🔑 {admin.username} (ID: {admin.id}, Role: {admin.role})")
                print(f"     Account ID: {admin.account_id}, Team ID: {admin.team_id}")
                
                # Simulate the filtering logic
                if admin.role == 'super_admin':
                    visible_requests = pending_requests
                    print(f"     ✅ Super admin - can see ALL {len(visible_requests)} requests")
                elif admin.role == 'account_admin':
                    visible_requests = [req for req in pending_requests if req.account_id == admin.account_id]
                    print(f"     Account admin - can see {len(visible_requests)} requests (account {admin.account_id})")
                elif admin.role == 'team_admin':
                    visible_requests = [req for req in pending_requests if req.account_id == admin.account_id and req.team_id == admin.team_id]
                    print(f"     Team admin - can see {len(visible_requests)} requests (account {admin.account_id}, team {admin.team_id})")
                
                if visible_requests:
                    for req in visible_requests:
                        print(f"       → Can approve Request ID {req.id}")
                else:
                    print(f"       ❌ CANNOT see any requests due to account/team mismatch!")
                print()
            
            # 3. Check the specific mismatch
            print("🔍 DETAILED ANALYSIS:")
            if pending_requests:
                req = pending_requests[0]  # Take first request as example
                print(f"Sample Request (ID {req.id}) requires:")
                print(f"  Account ID: {req.account_id}")
                print(f"  Team ID: {req.team_id}")
                print()
                
                print("Admin permission matching:")
                for admin in admin_users:
                    if admin.role == 'super_admin':
                        match = "✅ MATCHES (super admin sees all)"
                    elif admin.role == 'account_admin':
                        match = "✅ MATCHES" if admin.account_id == req.account_id else f"❌ MISMATCH (admin account {admin.account_id} != request account {req.account_id})"
                    elif admin.role == 'team_admin':
                        account_match = admin.account_id == req.account_id
                        team_match = admin.team_id == req.team_id
                        if account_match and team_match:
                            match = "✅ MATCHES"
                        else:
                            match = f"❌ MISMATCH (admin: account {admin.account_id}, team {admin.team_id} vs request: account {req.account_id}, team {req.team_id})"
                    
                    print(f"  {admin.username} ({admin.role}): {match}")
            
            # 4. Check notifications sent
            print(f"\n📧 NOTIFICATIONS ANALYSIS:")
            from models.shift_swap_leave import SwapLeaveNotification
            notifications = SwapLeaveNotification.query.filter_by(
                notification_type='swap_request_pending'
            ).order_by(SwapLeaveNotification.created_at.desc()).limit(10).all()
            
            print(f"Recent swap request notifications ({len(notifications)}):")
            for notif in notifications:
                recipient = User.query.get(notif.recipient_id)
                print(f"  📤 To: {recipient.username if recipient else 'Unknown'} (ID: {notif.recipient_id})")
                print(f"     Role: {recipient.role if recipient else 'Unknown'}")
                print(f"     Read: {'Yes' if notif.is_read else 'No'}")
                print(f"     Created: {notif.created_at}")
                print()
            
            print("💡 CONCLUSION:")
            print("The issue is likely account/team ID mismatches between admins and requests.")
            print("Admins need to be in the same account/team as the requests to see them.")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    diagnose_approval_filtering()