#!/bin/bash
# Debug Dashboard Notifications
echo "🔍 DEBUGGING DASHBOARD NOTIFICATIONS"
echo "=================================="

echo "1. Checking if dashboard notification JavaScript is being called..."
echo "   Open browser console (F12) and look for these messages:"
echo "   - 'Loading dashboard notifications...' (should appear on page load)"
echo "   - 'Dashboard notifications loaded: X assignments' (if successful)"
echo "   - Any error messages about API calls"

echo -e "\n2. Testing API endpoint directly..."
docker-compose exec -T web python -c "
import sys
import json
sys.path.append('/app')

try:
    from app import app
    from routes.incident_assignment import get_pending_assignments
    from models.models import User
    from flask import g
    from flask_login import login_user
    
    with app.app_context():
        with app.test_request_context():
            print('🧪 TESTING API ENDPOINT DIRECTLY')
            print('================================')
            
            # Test for david_ops (user ID 12)
            user = User.query.get(12)
            if user:
                # Simulate login
                from unittest.mock import patch
                with patch('flask_login.current_user', user):
                    print(f'Testing as user: {user.username} (ID: {user.id})')
                    
                    # Import and test the function
                    from models.handover_enhanced import IncidentAssignment
                    
                    # Direct query test
                    pending_assignments = IncidentAssignment.query.filter_by(
                        assigned_to_id=user.id,
                        assignment_status='pending'
                    ).all()
                    
                    print(f'Direct query result: {len(pending_assignments)} pending assignments')
                    
                    for assignment in pending_assignments:
                        print(f'  - {assignment.incident_id}: {assignment.incident_title}')
                        print(f'    Priority: {assignment.incident_priority}')
                    
                    # Test assignment data structure
                    if pending_assignments:
                        test_assignment = pending_assignments[0]
                        assigner = User.query.get(test_assignment.assigned_by_id)
                        
                        assignment_data = {
                            'id': test_assignment.id,
                            'incident_id': test_assignment.incident_id,
                            'incident_title': test_assignment.incident_title,
                            'incident_description': test_assignment.incident_description,
                            'incident_priority': test_assignment.incident_priority,
                            'assigned_by': assigner.username if assigner else 'Unknown',
                            'handover_context': test_assignment.handover_context,
                            'created_at': test_assignment.assigned_at.strftime('%Y-%m-%d %H:%M') if test_assignment.assigned_at else 'Unknown'
                        }
                        
                        print('\\nSample assignment data structure:')
                        print(json.dumps(assignment_data, indent=2))
                    
            else:
                print('❌ User david_ops (ID: 12) not found')

except Exception as e:
    print(f'❌ API test error: {e}')
    import traceback
    traceback.print_exc()
"

echo -e "\n3. Checking dashboard HTML structure..."
echo "Verifying notification panel elements exist:"

# Check if notification elements exist
if grep -q 'id=\"incident-notifications-dashboard\"' templates/dashboard.html; then
    echo "✅ Main notification panel exists"
else
    echo "❌ Main notification panel missing"
fi

if grep -q 'id=\"notifications-count\"' templates/dashboard.html; then
    echo "✅ Notification count element exists"
else
    echo "❌ Notification count element missing"
fi

if grep -q 'id=\"notifications-summary\"' templates/dashboard.html; then
    echo "✅ Notification summary element exists"
else
    echo "❌ Notification summary element missing"
fi

echo -e "\n4. Current assignment status for debugging..."
docker-compose exec -T db mysql -u root -prootpassword shift_handover << 'EOF'
SELECT 'ASSIGNMENTS FOR DASHBOARD TESTING:' as info;
SELECT 
    ia.id,
    ia.incident_id,
    ia.incident_title,
    ia.incident_priority,
    ia.assignment_status,
    ia.assigned_to_id,
    u.username as assigned_to,
    ia.assigned_at
FROM incident_assignment ia
LEFT JOIN user u ON ia.assigned_to_id = u.id
WHERE ia.assignment_status = 'pending' AND ia.assigned_to_id IN (1, 12)
ORDER BY ia.assigned_at DESC;
EOF

echo -e "\n🔧 DASHBOARD DEBUGGING STEPS:"
echo "=============================================="
echo "1. 🌐 Open: http://[YOUR_GCP_VM_IP]:5000"
echo "2. 🔑 Login as: david_ops"
echo "3. 📊 Go to: Dashboard"
echo "4. 🔍 Open browser console (F12)"
echo "5. 👀 Look for these JavaScript messages:"
echo "   - Console logs about loading notifications"
echo "   - Any error messages about fetch requests"
echo "   - Network tab to see if /api/get_pending_assignments is called"
echo ""
echo "🎯 EXPECTED BEHAVIOR:"
echo "- Dashboard should show orange notification panel at top"
echo "- Panel should show 'You have X pending incident assignment(s)'"
echo "- Should list assignments with Accept/Reject buttons"
echo ""
echo "🚨 IF STILL NOT WORKING:"
echo "1. Check browser console for JavaScript errors"
echo "2. Check network tab for failed API calls"
echo "3. Verify user is properly logged in"
echo "4. Check if dashboard JavaScript is loading properly"
