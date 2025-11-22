#!/usr/bin/env python3
"""
Fix the My Requests section to show all user requests (not just pending)
"""

def fix_my_requests_display():
    """Fix the My Requests section in the dashboard template"""
    
    print("🔧 FIXING MY REQUESTS DISPLAY")
    print("=" * 60)
    
    try:
        template_file = '/home/shifthandoversajid/shift_handover_app/templates/shift_management/dashboard.html'
        
        with open(template_file, 'r') as f:
            content = f.read()
        
        # Check if the user_requests data is being properly used
        if 'user_requests.swap_requests' in content:
            print('✅ Template references user_requests.swap_requests')
        else:
            print('❌ Template may not be using user_requests properly')
        
        # The issue might be that the template is checking for user_requests incorrectly
        # Let me fix the template logic
        
        # Look for the My Requests section and ensure it's showing data correctly
        old_swap_section = '''{% if user_requests and user_requests.swap_requests %}
                                    <div class="requests-list">
                                        {% for request in user_requests.swap_requests %}'''
        
        new_swap_section = '''{% if user_requests and user_requests.swap_requests and user_requests.swap_requests|length > 0 %}
                                    <div class="requests-list">
                                        {% for request in user_requests.swap_requests %}'''
        
        if old_swap_section in content:
            content = content.replace(old_swap_section, new_swap_section)
            print('✅ Updated swap requests condition')
        
        # Similar fix for leave requests
        old_leave_section = '''{% if user_requests and user_requests.leave_requests %}
                                    <div class="requests-list">
                                        {% for request in user_requests.leave_requests %}'''
        
        new_leave_section = '''{% if user_requests and user_requests.leave_requests and user_requests.leave_requests|length > 0 %}
                                    <div class="requests-list">
                                        {% for request in user_requests.leave_requests %}'''
        
        if old_leave_section in content:
            content = content.replace(old_leave_section, new_leave_section)
            print('✅ Updated leave requests condition')
        
        # Also add some debug information to see what's being passed
        debug_section = '''
            <!-- Debug: User Requests Data -->
            <div style="display: none;">
                Debug: user_requests = {{ user_requests }}
                {% if user_requests %}
                    Swap count: {{ user_requests.swap_requests|length if user_requests.swap_requests else 0 }}
                    Leave count: {{ user_requests.leave_requests|length if user_requests.leave_requests else 0 }}
                {% endif %}
            </div>
        '''
        
        # Add debug section before the My Requests section
        if 'My Requests' in content and 'Debug: User Requests Data' not in content:
            content = content.replace(
                '<div class="card-header bg-primary text-white">',
                debug_section + '\n        <div class="card-header bg-primary text-white">',
                1  # Only replace the first occurrence
            )
            print('✅ Added debug information')
        
        with open(template_file, 'w') as f:
            f.write(content)
        
        print("✅ Fixed My Requests display logic")
        
    except Exception as e:
        print(f"❌ Error fixing My Requests display: {e}")
        import traceback
        traceback.print_exc()

def create_test_pending_requests():
    """Create some pending requests for testing"""
    
    print(f"\n🔧 CREATING TEST PENDING REQUESTS")
    print("=" * 60)
    
    try:
        from app import app, db
        
        with app.app_context():
            from models.models import User
            from models.shift_swap_leave import ShiftSwapRequest, LeaveRequest
            from datetime import datetime, timedelta
            
            # Find techopsuser1
            user = User.query.filter_by(username='techopsuser1').first()
            if not user:
                print('❌ User techopsuser1 not found')
                return
            
            # Find another user to swap with
            swap_user = User.query.filter(User.id != user.id).first()
            if not swap_user:
                print('❌ No other user found for swap')
                return
            
            print(f'Creating test requests for {user.username} (ID: {user.id})')
            
            # Create a pending swap request
            swap_request = ShiftSwapRequest(
                requester_id=user.id,
                swap_with_id=swap_user.id,
                original_date=datetime.now().date() + timedelta(days=1),
                original_shift_code='D',
                swap_date=datetime.now().date() + timedelta(days=2),
                swap_shift_code='E',
                reason='Test pending swap request',
                status='pending',
                created_at=datetime.utcnow()
            )
            
            # Create a pending leave request
            leave_request = LeaveRequest(
                requester_id=user.id,
                leave_date=datetime.now().date() + timedelta(days=3),
                leave_type='personal',
                shift_code='D',
                reason='Test pending leave request',
                status='pending',
                created_at=datetime.utcnow()
            )
            
            db.session.add(swap_request)
            db.session.add(leave_request)
            db.session.commit()
            
            print(f'✅ Created pending swap request ID: {swap_request.id}')
            print(f'✅ Created pending leave request ID: {leave_request.id}')
            
    except Exception as e:
        print(f"❌ Error creating test requests: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    fix_my_requests_display()
    create_test_pending_requests()