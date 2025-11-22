#!/usr/bin/env python3
"""
Debug the approval endpoint directly to find the exact issue
"""
import sys
import os

# Add the current directory to Python path
sys.path.append('/app')

def debug_approval_endpoint():
    """Debug the approval endpoint and check for issues"""
    
    print("🔍 DEBUGGING APPROVAL ENDPOINT")
    print("=" * 60)
    
    try:
        # Import Flask app and test the route directly
        from app import app
        from services.shift_swap_leave_service import ShiftSwapLeaveService
        from models.shift_swap_leave import ShiftSwapRequest
        
        with app.app_context():
            # Check the current state of Request ID 2
            request = ShiftSwapRequest.query.get(2)
            if request:
                print(f"📋 Request ID 2 Details:")
                print(f"  • Status: {request.status}")
                print(f"  • Requester: {request.requester_username}")
                print(f"  • Partner: {request.partner_username}")
                print(f"  • Date: {request.shift_date}")
                print(f"  • Created: {request.created_at}")
                print(f"  • Updated: {request.updated_at}")
                
                # Try to approve it directly through the service
                print(f"\n🧪 Testing Direct Approval...")
                service = ShiftSwapLeaveService()
                result = service.approve_swap_request(2, approved_by_username='superadmin', comments='Debug test approval')
                
                print(f"✅ Direct Approval Result: {result}")
                
                # Check the request status after approval attempt
                request = ShiftSwapRequest.query.get(2)
                print(f"📋 Request Status After Approval: {request.status}")
                
            else:
                print("❌ Request ID 2 not found!")
                
            # Let's also check what happens when we simulate the exact route call
            print(f"\n🌐 Testing Route Endpoint...")
            
            # Import the route function
            from routes.shift_swap_leave import approve_swap_request_route
            
            # Create a test request context
            with app.test_request_context('/shift-management/admin/approve-swap/2', method='POST', json={'comments': 'Test approval'}):
                try:
                    response = approve_swap_request_route(2)
                    print(f"✅ Route Response: {response}")
                except Exception as route_error:
                    print(f"❌ Route Error: {route_error}")
                    import traceback
                    traceback.print_exc()
            
            # Check if there are any database constraints or issues
            print(f"\n🔧 Database Constraint Check...")
            from extensions import db
            
            # Check foreign key constraints
            print("Checking database integrity...")
            try:
                db.session.execute("PRAGMA foreign_key_check;")
                print("✅ Database integrity OK")
            except Exception as db_error:
                print(f"❌ Database error: {db_error}")
                
    except Exception as e:
        print(f"❌ Error during debugging: {e}")
        import traceback
        traceback.print_exc()

def check_route_registration():
    """Check if the approval route is properly registered"""
    
    print(f"\n🛣️ CHECKING ROUTE REGISTRATION")
    print("=" * 60)
    
    try:
        from app import app
        
        with app.app_context():
            # List all routes
            print("📋 All Registered Routes:")
            for rule in app.url_map.iter_rules():
                if 'approve-swap' in rule.rule:
                    print(f"  • {rule.rule} -> {rule.endpoint} [{rule.methods}]")
                    
            # Check if the blueprint is registered
            print(f"\n📋 Registered Blueprints:")
            for name, blueprint in app.blueprints.items():
                if 'shift' in name.lower():
                    print(f"  • {name}: {blueprint.url_prefix}")
                    
    except Exception as e:
        print(f"❌ Error checking routes: {e}")

def test_manual_approval():
    """Test manual approval with detailed logging"""
    
    print(f"\n🔧 MANUAL APPROVAL TEST")
    print("=" * 60)
    
    try:
        from app import app
        from extensions import db
        from models.shift_swap_leave import ShiftSwapRequest
        from models.shift_roster import ShiftRoster
        from datetime import datetime
        
        with app.app_context():
            # Get the request
            request = ShiftSwapRequest.query.get(2)
            if not request:
                print("❌ Request not found")
                return
                
            print(f"📋 Request found: {request.requester_username} ↔ {request.partner_username}")
            print(f"📅 Shift Date: {request.shift_date}")
            
            # Check roster entries
            requester_roster = ShiftRoster.query.filter_by(
                username=request.requester_username,
                shift_date=request.shift_date
            ).first()
            
            partner_roster = ShiftRoster.query.filter_by(
                username=request.partner_username,
                shift_date=request.shift_date
            ).first()
            
            print(f"📋 Requester Roster: {requester_roster.shift_code if requester_roster else 'NOT FOUND'}")
            print(f"📋 Partner Roster: {partner_roster.shift_code if partner_roster else 'NOT FOUND'}")
            
            if requester_roster and partner_roster:
                print(f"\n🔄 Swapping shifts...")
                print(f"  • {request.requester_username}: {requester_roster.shift_code} → {partner_roster.shift_code}")
                print(f"  • {request.partner_username}: {partner_roster.shift_code} → {requester_roster.shift_code}")
                
                # Perform the swap
                temp_shift = requester_roster.shift_code
                requester_roster.shift_code = partner_roster.shift_code
                partner_roster.shift_code = temp_shift
                
                # Update request status
                request.status = 'approved'
                request.approved_by_username = 'superadmin'
                request.approved_at = datetime.utcnow()
                request.comments = 'Manual approval test'
                
                # Commit changes
                db.session.commit()
                
                print(f"✅ Manual approval completed successfully!")
                
                # Verify the changes
                updated_request = ShiftSwapRequest.query.get(2)
                print(f"📋 Updated Status: {updated_request.status}")
                
            else:
                print("❌ One or both roster entries not found - cannot swap")
                
    except Exception as e:
        print(f"❌ Manual approval error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_approval_endpoint()
    check_route_registration()
    test_manual_approval()