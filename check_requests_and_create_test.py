#!/usr/bin/env python3
"""
Check current state of all requests and create a new test request
"""
import sys
import os

# Add the current directory to Python path
sys.path.append('/app')

def check_all_requests():
    """Check all shift swap requests"""
    
    print("🔍 CHECKING ALL SHIFT SWAP REQUESTS")
    print("=" * 60)
    
    try:
        from app import app
        from config import db
        from models.shift_swap_leave import ShiftSwapRequest
        
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
                print(f"  • Approved By: {req.approved_by_username}")
                print(f"  • Approved At: {req.approved_at}")
                print("-" * 40)
                
            # Check pending requests specifically
            pending_requests = ShiftSwapRequest.query.filter_by(status='pending').all()
            print(f"⏳ Pending Requests: {len(pending_requests)}")
            
            if pending_requests:
                for req in pending_requests:
                    print(f"🆔 Pending Request ID: {req.id}")
                    print(f"  • Requester: User ID {req.requester_user_id}")
                    print(f"  • Partner: User ID {req.partner_user_id}")
                    print(f"  • Date: {req.shift_date}")
            
            # Let's also get the usernames
            from models.user import User
            print(f"\n👤 USER MAPPINGS:")
            users = User.query.all()
            for user in users:
                print(f"  • ID {user.id}: {user.username}")
                    
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

def create_test_request():
    """Create a new test request for approval testing"""
    
    print(f"\n🆕 CREATING NEW TEST REQUEST")
    print("=" * 60)
    
    try:
        from app import app
        from config import db
        from models.shift_swap_leave import ShiftSwapRequest
        from models.user import User
        from datetime import datetime, timedelta
        
        with app.app_context():
            # Find two different users
            users = User.query.limit(5).all()
            print(f"👤 Available Users:")
            for user in users:
                print(f"  • ID {user.id}: {user.username}")
            
            if len(users) >= 2:
                # Create a new swap request
                future_date = datetime.now() + timedelta(days=2)
                
                new_request = ShiftSwapRequest(
                    requester_user_id=users[0].id,
                    partner_user_id=users[1].id,
                    shift_date=future_date.date(),
                    reason="Test swap request for approval testing",
                    status='pending'
                )
                
                db.session.add(new_request)
                db.session.commit()
                
                print(f"✅ Created Test Request ID: {new_request.id}")
                print(f"  • Requester: {users[0].username} (ID: {users[0].id})")
                print(f"  • Partner: {users[1].username} (ID: {users[1].id})")
                print(f"  • Date: {future_date.date()}")
                print(f"  • Status: {new_request.status}")
                
            else:
                print("❌ Not enough users to create a test request")
                
    except Exception as e:
        print(f"❌ Error creating test request: {e}")
        import traceback
        traceback.print_exc()

def fix_dashboard_template():
    """Fix the dashboard template to handle both user ID and username"""
    
    print(f"\n🔧 FIXING DASHBOARD TEMPLATE")
    print("=" * 60)
    
    try:
        template_path = '/app/templates/shift_management/dashboard.html'
        
        with open(template_path, 'r') as f:
            content = f.read()
        
        # Fix the template to show proper user information
        # Replace the table rows to show user IDs properly
        old_table_row = '''<tr>
                                <td>{{ request.id }}</td>
                                <td>{{ request.requester_username }}</td>
                                <td>{{ request.partner_username }}</td>
                                <td>{{ request.shift_date }}</td>
                                <td>{{ request.reason }}</td>
                                <td>
                                    <button class="btn btn-success btn-sm" onclick="approveSwapRequest({{ request.id }})">
                                        <i class="fas fa-check"></i> Approve
                                    </button>
                                    <button class="btn btn-danger btn-sm" onclick="rejectSwapRequest({{ request.id }})">
                                        <i class="fas fa-times"></i> Reject
                                    </button>
                                </td>
                            </tr>'''
        
        new_table_row = '''<tr>
                                <td>{{ request.id }}</td>
                                <td>User ID: {{ request.requester_user_id }}</td>
                                <td>User ID: {{ request.partner_user_id }}</td>
                                <td>{{ request.shift_date }}</td>
                                <td>{{ request.reason }}</td>
                                <td>
                                    <button class="btn btn-success btn-sm" onclick="approveSwapRequest({{ request.id }})">
                                        <i class="fas fa-check"></i> Approve
                                    </button>
                                    <button class="btn btn-danger btn-sm" onclick="rejectSwapRequest({{ request.id }})">
                                        <i class="fas fa-times"></i> Reject
                                    </button>
                                </td>
                            </tr>'''
        
        if old_table_row in content:
            content = content.replace(old_table_row, new_table_row)
            
            with open(template_path, 'w') as f:
                f.write(content)
            
            print("✅ Fixed dashboard template to show User IDs")
        else:
            print("⚠️ Table row pattern not found - template might be different")
            
    except Exception as e:
        print(f"❌ Error fixing template: {e}")

if __name__ == "__main__":
    check_all_requests()
    create_test_request()
    fix_dashboard_template()