#!/bin/bash
# DEBUG DASHBOARD NOTIFICATIONS ISSUE
echo "🔍 DEBUGGING DASHBOARD NOTIFICATIONS ISSUE"
echo "=========================================="

echo "🎯 Issue: Dashboard notifications working locally but not in prod"
echo "📊 Current user in logs: sajid_mohammad@epam.com (ID: 18)"

echo -e "\n🧪 Testing dashboard notifications for current user..."
docker-compose exec -T web python -c "
try:
    from app import app
    from models.handover_enhanced import IncidentAssignment
    from models.models import User
    
    with app.app_context():
        print('🧪 TESTING DASHBOARD NOTIFICATIONS')
        print('=================================')
        
        # Test current user (ID: 18)
        current_user = User.query.get(18)
        if current_user:
            print(f'Current user: {current_user.username} (ID: {current_user.id})')
            
            # Check assignments for current user
            assignments = IncidentAssignment.query.filter_by(
                assigned_to_id=current_user.id,
                assignment_status='pending'
            ).all()
            
            print(f'Pending assignments for current user: {len(assignments)}')
            
            if len(assignments) == 0:
                print('❌ This user has NO pending assignments - that\\'s why dashboard is empty!')
                print('')
                print('✅ Solution: Log in as a user who has assignments:')
                
                # Show users with assignments
                users_with_assignments = User.query.join(IncidentAssignment, User.id == IncidentAssignment.assigned_to_id).filter(IncidentAssignment.assignment_status == 'pending').distinct().all()
                
                for user in users_with_assignments:
                    user_assignments = IncidentAssignment.query.filter_by(
                        assigned_to_id=user.id,
                        assignment_status='pending'
                    ).all()
                    print(f'  - {user.username} (ID: {user.id}) has {len(user_assignments)} pending assignments')
            else:
                for assignment in assignments:
                    print(f'  - Assignment {assignment.id}: {assignment.incident_id}')
        else:
            print('❌ User ID 18 not found')

except Exception as e:
    print(f'❌ Test failed: {e}')
    import traceback
    traceback.print_exc()
"

echo -e "\n🌐 Testing API endpoint response for current session..."
echo "When you access dashboard, it should call /api/get_pending_assignments"
echo "This API uses current_user.id from the session"

echo -e "\n📱 DASHBOARD DEBUGGING STEPS:"
echo "============================="
echo ""
echo "1. Open your dashboard page: http://your-vm-ip/"
echo "2. Open browser dev tools (F12)"
echo "3. Look in Console tab for these messages:"
echo "   - '🔔 Loading dashboard notifications...'"
echo "   - '📡 API Response status: 200'"
echo "   - '📊 API Response data: {...}'"
echo "   - Check if assignments array is empty or has data"
echo ""
echo "4. Check Network tab for:"
echo "   - GET request to /api/get_pending_assignments"
echo "   - Response status (should be 200)"
echo "   - Response data (should show success: true, assignments: [...])"

echo -e "\n🔧 TESTING WITH USERS WHO HAVE ASSIGNMENTS:"
echo "==========================================="
echo ""
echo "The current user (sajid_mohammad@epam.com) likely has no assignments."
echo "To see dashboard notifications, log in as:"
echo ""
echo "1. SUPERADMIN (username: superadmin)"
echo "   - Should have 3 pending assignments"
echo "   - Dashboard should show notification panel"
echo ""
echo "2. DAVID_OPS (username: david_ops)" 
echo "   - Should have 2 pending assignments"
echo "   - Dashboard should show notification panel"

echo -e "\n📊 WHAT DASHBOARD NOTIFICATIONS SHOULD LOOK LIKE:"
echo "=============================================="
echo ""
echo "When user has pending assignments:"
echo "✅ Yellow notification panel appears at top of dashboard"
echo "✅ Shows: 'You have X pending incident assignment(s)'"
echo "✅ Has 'View All' and toggle buttons"
echo "✅ Can expand to show detailed list"
echo ""
echo "When user has no assignments:"
echo "❌ Notification panel stays hidden (display: none)"
echo "❌ Dashboard looks normal without notification bar"

echo -e "\n🚀 SOLUTION STEPS:"
echo "=================="
echo ""
echo "1. VERIFY CURRENT USER ISSUE:"
echo "   - Log in as superadmin or david_ops"
echo "   - Go to dashboard"
echo "   - Should see notification panel"
echo ""
echo "2. IF STILL NO NOTIFICATIONS WITH CORRECT USER:"
echo "   - Check browser console for JavaScript errors"
echo "   - Check Network tab for API call failures"
echo "   - Look for CORS or authentication issues"
echo ""
echo "3. CHECK API DIRECTLY:"
echo "   - While logged in as superadmin, visit: /api/get_pending_assignments"
echo "   - Should return JSON with assignments data"

echo -e "\n🎯 MOST LIKELY CAUSE:"
echo "===================="
echo "You're testing with a user who has no incident assignments."
echo "Dashboard notifications only appear when the logged-in user has pending assignments."
echo ""
echo "✅ Try logging in as 'superadmin' and checking the dashboard!"
echo "📊 The notification panel should appear at the top with assignment details."
