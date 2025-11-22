#!/usr/bin/env python3
"""
Test and fix the approval process end-to-end
"""
import sys
import os

# Add the current directory to Python path
sys.path.append('/app')

def test_and_fix_approval():
    """Test the approval process and fix any issues"""
    
    print("🔧 TESTING AND FIXING APPROVAL PROCESS")
    print("=" * 60)
    
    try:
        from app import app, db
        from services.shift_swap_leave_service import shift_swap_leave_service
        from models.shift_swap_leave import ShiftSwapRequest
        from models.models import User
        from flask import Flask
        
        with app.app_context():
            print("✅ Flask app context loaded")
            
            # Get test data
            pending_request = ShiftSwapRequest.query.filter_by(status='pending').first()
            admin_user = User.query.filter_by(role='super_admin').first()
            
            if not pending_request:
                print("❌ No pending requests found for testing")
                return
                
            if not admin_user:
                print("❌ No admin user found for testing")
                return
                
            print(f"✅ Test data found:")
            print(f"  Request ID: {pending_request.id}")
            print(f"  Requester ID: {pending_request.requester_id}")
            print(f"  Swap with ID: {pending_request.swap_with_id}")
            print(f"  Admin user: {admin_user.username} (ID: {admin_user.id})")
            
            # Test Step 1: Check if users exist
            print("\n🔍 Step 1: Checking if users exist...")
            requester = User.query.get(pending_request.requester_id)
            swap_with = User.query.get(pending_request.swap_with_id)
            
            print(f"  Requester: {requester.username if requester else 'NOT FOUND'}")
            print(f"  Swap with: {swap_with.username if swap_with else 'NOT FOUND'}")
            
            # Test Step 2: Check team member mappings
            print("\n🔍 Step 2: Checking team member mappings...")
            
            def get_team_member_id_for_user(user_id):
                user = User.query.get(user_id)
                if not user:
                    return None
                
                from models.models import TeamMember
                team_member = TeamMember.query.filter_by(
                    name=user.username,
                    account_id=user.account_id,
                    team_id=user.team_id
                ).first()
                
                return team_member.id if team_member else None
            
            requester_tm_id = get_team_member_id_for_user(pending_request.requester_id)
            swap_with_tm_id = get_team_member_id_for_user(pending_request.swap_with_id)
            
            print(f"  Requester team member ID: {requester_tm_id}")
            print(f"  Swap with team member ID: {swap_with_tm_id}")
            
            if not requester_tm_id or not swap_with_tm_id:
                print("❌ Missing team member mappings - this will cause approval to fail")
                
                # Fix: Create missing team member mappings
                print("🔧 Creating missing team member mappings...")
                
                from models.models import TeamMember
                
                if not requester_tm_id and requester:
                    new_tm = TeamMember(
                        name=requester.username,
                        account_id=requester.account_id,
                        team_id=requester.team_id,
                        email=requester.email,
                        shift_timings='{"Morning": "09:00-17:00", "Evening": "17:00-01:00", "Night": "01:00-09:00"}'
                    )
                    db.session.add(new_tm)
                    db.session.flush()
                    requester_tm_id = new_tm.id
                    print(f"  ✅ Created team member for {requester.username} (ID: {requester_tm_id})")
                
                if not swap_with_tm_id and swap_with:
                    new_tm = TeamMember(
                        name=swap_with.username,
                        account_id=swap_with.account_id,
                        team_id=swap_with.team_id,
                        email=swap_with.email,
                        shift_timings='{"Morning": "09:00-17:00", "Evening": "17:00-01:00", "Night": "01:00-09:00"}'
                    )
                    db.session.add(new_tm)
                    db.session.flush()
                    swap_with_tm_id = new_tm.id
                    print(f"  ✅ Created team member for {swap_with.username} (ID: {swap_with_tm_id})")
                
                db.session.commit()
            else:
                print("✅ Team member mappings exist")
            
            # Test Step 3: Try the approval process
            print("\n🧪 Step 3: Testing approval process...")
            
            try:
                result = shift_swap_leave_service.approve_swap_request(
                    request_id=pending_request.id,
                    approver_id=admin_user.id,
                    comments="Test approval - will be rolled back"
                )
                
                if result.get('success'):
                    print("✅ Approval process completed successfully!")
                    print(f"  Result: {result}")
                    
                    # Check if the request status was updated
                    updated_request = ShiftSwapRequest.query.get(pending_request.id)
                    print(f"  Updated status: {updated_request.status}")
                    print(f"  Approved by: {updated_request.approved_by_id}")
                    print(f"  Approved at: {updated_request.approved_at}")
                    
                    # Rollback the test
                    db.session.rollback()
                    print("  🔄 Test approval rolled back")
                    
                else:
                    print(f"❌ Approval failed: {result.get('error')}")
                    
            except Exception as e:
                print(f"❌ Approval process error: {e}")
                import traceback
                traceback.print_exc()
                db.session.rollback()
            
            # Test Step 4: Test the HTTP endpoint simulation
            print("\n🌐 Step 4: Testing HTTP endpoint simulation...")
            
            try:
                # Simulate the request data
                request_data = {'comments': 'Test HTTP approval'}
                
                # This simulates what happens in the route
                result = shift_swap_leave_service.approve_swap_request(
                    request_id=pending_request.id,
                    approver_id=admin_user.id,
                    comments=request_data.get('comments', '')
                )
                
                if result.get('success'):
                    print("✅ HTTP endpoint simulation successful!")
                    db.session.rollback()  # Rollback test
                else:
                    print(f"❌ HTTP endpoint simulation failed: {result.get('error')}")
                    
            except Exception as e:
                print(f"❌ HTTP endpoint error: {e}")
                import traceback
                traceback.print_exc()
                db.session.rollback()
            
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_and_fix_approval()