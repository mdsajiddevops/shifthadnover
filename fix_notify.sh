#!/bin/bash
# FIX NOTIFICATIONS DISPLAY ISSUES
echo "🔧 FIXING NOTIFICATIONS DISPLAY ISSUES"
echo "======================================="

echo "✅ Backend API works correctly (confirmed by debug script)"
echo "✅ Database has correct data (superadmin has 3 assignments, david_ops has 2)"
echo "❌ Frontend notifications page not showing assignments"

echo -e "\n🧪 Testing the notifications route directly..."
docker-compose exec -T web python -c "
try:
    from app import app
    from flask import current_app
    from models.handover_enhanced import IncidentAssignment
    from models.models import User
    
    with app.app_context():
        print('🧪 TESTING NOTIFICATIONS ROUTE LOGIC')
        print('====================================')
        
        # Test for both users
        for username in ['superadmin', 'david_ops']:
            user = User.query.filter_by(username=username).first()
            if user:
                print(f'\\n👤 Testing for {username} (ID: {user.id})')
                
                # Simulate what the notifications route does
                all_assignments = IncidentAssignment.query.filter_by(
                    assigned_to_id=user.id
                ).order_by(IncidentAssignment.assigned_at.desc()).all()
                
                print(f'Found {len(all_assignments)} assignments for {username}')
                
                incident_assignments = []
                for assignment in all_assignments:
                    assigner = User.query.get(assignment.assigned_by_id)
                    assigner_name = assigner.username if assigner else 'Unknown'
                    
                    incident_assignments.append({
                        'id': assignment.id,
                        'title': f'Incident Assignment: {assignment.incident_title}',
                        'type': 'incident',
                        'priority': assignment.incident_priority.lower() if assignment.incident_priority else 'medium',
                        'assignment_status': assignment.assignment_status,
                        'incident_id': assignment.incident_id
                    })
                    
                    print(f'  - Assignment {assignment.id}: {assignment.incident_id} ({assignment.assignment_status})')
                
                print(f'Created {len(incident_assignments)} notification items for {username}')

except Exception as e:
    print(f'❌ Test failed: {e}')
    import traceback
    traceback.print_exc()
"

echo -e "\n🔗 Testing if notification route is accessible..."
echo "Checking if the notifications route imports work..."
docker-compose exec -T web python -c "
try:
    import sys
    sys.path.append('/app')
    
    # Test the exact imports from the route
    from routes.user_profile import user_profile_bp
    from models.handover_enhanced import IncidentAssignment
    from models.models import User
    from flask_login import current_user
    
    print('✅ All imports work correctly')
    print('✅ Route blueprint exists')
    print('✅ Models can be imported')
    
except ImportError as e:
    print(f'❌ Import error: {e}')
except Exception as e:
    print(f'❌ Other error: {e}')
"

echo -e "\n📋 Manual browser testing steps:"
echo "================================"
echo ""
echo "1. Log in as superadmin"
echo "2. Go to: http://your-vm-ip/notifications"
echo "3. Open browser dev tools (F12)"
echo "4. Check for any JavaScript errors"
echo "5. Look at the page source - search for 'incident assignment'"
echo "6. Check if the HTML contains any assignment data"
echo ""
echo "7. Log in as david_ops"
echo "8. Go to: http://your-vm-ip/notifications"
echo "9. Repeat the same checks"
echo ""

echo -e "\n🚨 If notifications still don't show, check:"
echo "=========================================="
echo ""
echo "1. ROUTE REGISTRATION:"
echo "   - Check if user_profile blueprint is registered in app.py"
echo "   - Verify /notifications route is accessible"
echo ""
echo "2. TEMPLATE RENDERING:"
echo "   - Check if notifications.html template exists"
echo "   - Verify the template is getting the 'notifications' variable"
echo ""
echo "3. DATA FLOW:"
echo "   - Check server logs: docker-compose logs web | grep NOTIFICATIONS"
echo "   - Look for debug messages from the notifications route"
echo ""
echo "4. BROWSER CACHE:"
echo "   - Clear browser cache completely"
echo "   - Try hard refresh (Ctrl+F5)"
echo "   - Try incognito/private browser window"

echo -e "\n🔍 Debugging commands:"
echo "====================="
echo ""
echo "Check server logs for notifications:"
echo "docker-compose logs web | grep -i notification"
echo ""
echo "Check if route is registered:"
echo "docker-compose exec web python -c \"from app import app; print([rule.rule for rule in app.url_map.iter_rules() if 'notification' in rule.rule])\""
echo ""
echo "Test route accessibility:"
echo "curl -i http://your-vm-ip/notifications (will show 302 redirect if auth required)"

echo -e "\n🎯 MOST LIKELY ISSUE:"
echo "===================="
echo "The notifications route exists and should work, but either:"
echo "1. Browser cache is showing old version"
echo "2. Template is not rendering the data correctly"
echo "3. JavaScript errors are preventing display"
echo "4. Route debug messages will show what's happening"
echo ""
echo "✅ Try the browser testing steps above first!"
echo "📊 Share any console errors or server log messages you see"
