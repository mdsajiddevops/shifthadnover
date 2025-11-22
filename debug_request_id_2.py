#!/usr/bin/env python3
"""
Debug Request ID 2 approval issue and check leave request page
"""
import sys
import os

# Add the current directory to Python path
sys.path.append('/app')

def debug_request_id_2():
    """Debug why Request ID 2 approval fails"""
    
    print("🔍 DEBUGGING REQUEST ID 2 APPROVAL ISSUE")
    print("=" * 60)
    
    try:
        from app import app, db
        from services.shift_swap_leave_service import shift_swap_leave_service
        from models.shift_swap_leave import ShiftSwapRequest
        from models.models import User
        
        with app.app_context():
            # Get Request ID 2 specifically
            request_2 = ShiftSwapRequest.query.get(2)
            admin_user = User.query.filter_by(role='super_admin').first()
            
            if not request_2:
                print("❌ Request ID 2 not found!")
                return
                
            print(f"✅ Found Request ID 2:")
            print(f"  Status: {request_2.status}")
            print(f"  Requester ID: {request_2.requester_id}")
            print(f"  Swap with ID: {request_2.swap_with_id}")
            print(f"  Account ID: {request_2.account_id}")
            print(f"  Team ID: {request_2.team_id}")
            
            # Check users exist
            requester = User.query.get(request_2.requester_id)
            swap_with = User.query.get(request_2.swap_with_id)
            
            print(f"  Requester: {requester.username if requester else 'NOT FOUND'}")
            print(f"  Swap with: {swap_with.username if swap_with else 'NOT FOUND'}")
            
            # Check team member mappings
            from models.models import TeamMember
            
            requester_tm = TeamMember.query.filter_by(
                name=requester.username,
                account_id=requester.account_id,
                team_id=requester.team_id
            ).first() if requester else None
            
            swap_with_tm = TeamMember.query.filter_by(
                name=swap_with.username,
                account_id=swap_with.account_id,
                team_id=swap_with.team_id
            ).first() if swap_with else None
            
            print(f"  Requester TM: {requester_tm.id if requester_tm else 'NOT FOUND'}")
            print(f"  Swap with TM: {swap_with_tm.id if swap_with_tm else 'NOT FOUND'}")
            
            # Try to approve Request ID 2
            print(f"\n🧪 Testing approval of Request ID 2...")
            
            try:
                result = shift_swap_leave_service.approve_swap_request(
                    request_id=2,
                    approver_id=admin_user.id,
                    comments="Testing Request ID 2 approval"
                )
                
                if result.get('success'):
                    print("✅ Request ID 2 approval successful!")
                    print(f"  Result: {result}")
                    
                    # Check the updated status
                    updated_request = ShiftSwapRequest.query.get(2)
                    print(f"  New status: {updated_request.status}")
                    
                    # Rollback for safety
                    db.session.rollback()
                    print("  🔄 Test rolled back")
                    
                else:
                    print(f"❌ Request ID 2 approval failed: {result.get('error')}")
                    
                    # Let's dig deeper into the error
                    if 'team member' in result.get('error', '').lower():
                        print("\n🔧 Creating missing team member mappings...")
                        
                        if not requester_tm and requester:
                            new_tm = TeamMember(
                                name=requester.username,
                                account_id=requester.account_id,
                                team_id=requester.team_id,
                                email=requester.email,
                                shift_timings='{"Morning": "09:00-17:00", "Evening": "17:00-01:00", "Night": "01:00-09:00"}'
                            )
                            db.session.add(new_tm)
                            print(f"  ✅ Created team member for {requester.username}")
                        
                        if not swap_with_tm and swap_with:
                            new_tm = TeamMember(
                                name=swap_with.username,
                                account_id=swap_with.account_id,
                                team_id=swap_with.team_id,
                                email=swap_with.email,
                                shift_timings='{"Morning": "09:00-17:00", "Evening": "17:00-01:00", "Night": "01:00-09:00"}'
                            )
                            db.session.add(new_tm)
                            print(f"  ✅ Created team member for {swap_with.username}")
                        
                        db.session.commit()
                        print("  💾 Team member mappings saved")
                        
                        # Try approval again
                        print(f"\n🔄 Retrying approval after creating team members...")
                        
                        result = shift_swap_leave_service.approve_swap_request(
                            request_id=2,
                            approver_id=admin_user.id,
                            comments="Testing Request ID 2 approval after fix"
                        )
                        
                        if result.get('success'):
                            print("✅ Request ID 2 approval successful after fix!")
                            db.session.rollback()  # Rollback test
                        else:
                            print(f"❌ Still failing: {result.get('error')}")
                    
            except Exception as e:
                print(f"❌ Exception during approval: {e}")
                import traceback
                traceback.print_exc()
                db.session.rollback()
                
    except Exception as e:
        print(f"❌ Debug failed: {e}")
        import traceback
        traceback.print_exc()

def check_leave_request_template():
    """Check the current leave request template"""
    
    print(f"\n📄 CHECKING LEAVE REQUEST TEMPLATE")
    print("=" * 60)
    
    try:
        # Check if leave request template exists
        template_path = '/app/templates/shift_management/request_leave.html'
        
        if os.path.exists(template_path):
            print("✅ Leave request template found")
            
            with open(template_path, 'r') as f:
                content = f.read()
            
            # Check if it's using modern styling
            if 'modern-card' in content:
                print("✅ Template already has modern styling")
            else:
                print("❌ Template needs modern styling upgrade")
                
            if 'linear-gradient' in content:
                print("✅ Template has gradient styling")
            else:
                print("❌ Template needs gradient styling")
                
        else:
            print("❌ Leave request template not found!")
            
    except Exception as e:
        print(f"❌ Error checking template: {e}")

if __name__ == "__main__":
    debug_request_id_2()
    check_leave_request_template()