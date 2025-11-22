#!/bin/bash
# DEBUG NOTIFICATION ISSUES: Superadmin & Dashboard
echo "🔍 DEBUGGING NOTIFICATION DISPLAY ISSUES"
echo "========================================="

echo "🎯 Issues to investigate:"
echo "1. Superadmin notifications not showing (has pending assignments but no notifications)"
echo "2. Dashboard incident notifications not displaying"

echo -e "\n📊 Current assignment data:"
docker-compose exec -T db mysql -u root -prootpassword shift_handover << 'EOF'
SELECT 'ALL PENDING ASSIGNMENTS:' as info;
SELECT 
    ia.id,
    ia.incident_id,
    ia.incident_title,
    ia.assignment_status,
    ia.assigned_to_id,
    u.username as assigned_to
FROM incident_assignment ia
LEFT JOIN user u ON ia.assigned_to_id = u.id
WHERE ia.assignment_status = 'pending'
ORDER BY ia.assigned_to_id, ia.id DESC;

SELECT 'USER ID MAPPING:' as info;
SELECT id, username, email, role FROM user WHERE username IN ('david_ops', 'superadmin');
EOF

echo -e "\n🧪 Testing API endpoint directly for both users..."
echo "Testing for superadmin (user_id=1):"
docker-compose exec -T web python -c "
try:
    from app import app
    from models.handover_enhanced import IncidentAssignment
    from models.models import User
    
    with app.app_context():
        print('🧪 TESTING API ENDPOINT FOR SUPERADMIN')
        print('=====================================')
        
        # Test for superadmin (user_id=1)
        superadmin = User.query.filter_by(username='superadmin').first()
        if superadmin:
            print(f'Superadmin found: ID {superadmin.id}, Username: {superadmin.username}')
            
            # Query the same way the API does
            pending_assignments = IncidentAssignment.query.filter_by(
                assigned_to_id=superadmin.id,
                assignment_status='pending'
            ).all()
            
            print(f'Pending assignments for superadmin: {len(pending_assignments)}')
            for assignment in pending_assignments:
                print(f'  - ID {assignment.id}: {assignment.incident_id} ({assignment.incident_title})')
                
            # Test for david_ops too
            david = User.query.filter_by(username='david_ops').first()
            if david:
                david_assignments = IncidentAssignment.query.filter_by(
                    assigned_to_id=david.id,
                    assignment_status='pending'
                ).all()
                print(f'\\nPending assignments for david_ops: {len(david_assignments)}')
                for assignment in david_assignments:
                    print(f'  - ID {assignment.id}: {assignment.incident_id} ({assignment.incident_title})')
        else:
            print('❌ Superadmin user not found')

except Exception as e:
    print(f'❌ Test failed: {e}')
    import traceback
    traceback.print_exc()
"

echo -e "\n🔐 Testing user authentication and session..."
docker-compose exec -T web python -c "
try:
    from app import app
    from models.models import User
    from flask import session
    
    with app.app_context():
        print('🔐 USER AUTHENTICATION TEST')
        print('===========================')
        
        # Check user data
        users = User.query.filter(User.username.in_(['superadmin', 'david_ops'])).all()
        for user in users:
            print(f'User: {user.username} (ID: {user.id})')
            print(f'  - Email: {user.email}')
            print(f'  - Role: {user.role}')
            print(f'  - Active: {user.is_active if hasattr(user, \"is_active\") else \"Unknown\"}')

except Exception as e:
    print(f'❌ Auth test failed: {e}')
"

echo -e "\n🌐 Testing API endpoint manually..."
echo "You can test these URLs in browser or curl:"
echo "- http://your-vm-ip/api/get_pending_assignments (when logged in as superadmin)"
echo "- http://your-vm-ip/api/get_pending_assignments (when logged in as david_ops)"

echo -e "\n📱 Browser debugging steps:"
echo "==========================="
echo ""
echo "FOR SUPERADMIN NOTIFICATIONS:"
echo "1. Log in as superadmin"
echo "2. Go to notifications page"
echo "3. Open browser dev tools (F12)"
echo "4. In console, run: fetch('/api/get_pending_assignments').then(r => r.json()).then(console.log)"
echo "5. Check if API returns the 3 pending assignments"
echo ""
echo "FOR DASHBOARD NOTIFICATIONS:"
echo "1. Log in as any user with pending assignments"
echo "2. Go to dashboard page"
echo "3. Open browser dev tools (F12)"
echo "4. Look for console messages starting with '🔔 Loading dashboard notifications...'"
echo "5. Check if loadDashboardNotifications() is being called"
echo "6. Check if displayDashboardNotifications() receives data"

echo -e "\n🚨 COMMON ISSUES TO CHECK:"
echo "=========================="
echo ""
echo "1. USER SESSION ISSUES:"
echo "   - Is superadmin properly logged in?"
echo "   - Check cookies and session storage"
echo "   - Try logging out and back in as superadmin"
echo ""
echo "2. JAVASCRIPT ERRORS:"
echo "   - Look for any JavaScript errors in console"
echo "   - Check if loadDashboardNotifications function exists"
echo "   - Verify dashboard.html is loading properly"
echo ""
echo "3. API ENDPOINT ISSUES:"
echo "   - Check if /api/get_pending_assignments returns correct data"
echo "   - Verify user authentication in API calls"
echo "   - Check for any server-side errors in logs"
echo ""
echo "4. FRONTEND FILTERING:"
echo "   - Check if dashboard JavaScript is filtering notifications"
echo "   - Verify notification display logic"
echo "   - Look for any conditional rendering based on user role"

echo -e "\n📋 Quick fix to try:"
echo "==================="
echo "If superadmin login session is corrupted:"
echo "1. Log out completely"
echo "2. Clear browser cache/cookies"
echo "3. Log back in as superadmin" 
echo "4. Go to notifications page"
echo ""
echo "If dashboard notifications not loading:"
echo "1. Check browser console for JavaScript errors"
echo "2. Look for network requests to /api/get_pending_assignments"
echo "3. Verify the API response contains assignment data"

echo -e "\n🎯 Next steps after running this script:"
echo "========================================"
echo "1. Share the API test results above"
echo "2. Test the browser debugging steps"
echo "3. Check if superadmin can see notifications after fresh login"
echo "4. Report any JavaScript errors from dashboard page"
