#!/bin/bash
# DEBUG DASHBOARD NOTIFICATION ISSUE FOR DAVID_OPS USER
echo "🔍 DEBUGGING DASHBOARD NOTIFICATIONS FOR DAVID_OPS"
echo "================================================="

echo "✅ Confirmed: david_ops user (ID: 12) has 1 pending assignment"
echo "❌ Issue: Dashboard notification panel not showing"

echo -e "\n🧪 Testing API endpoint directly..."
docker-compose exec -T web python -c "
import json
from app import app
from flask import jsonify
from models.handover_enhanced import IncidentAssignment
from models.models import User

with app.app_context():
    print('🔍 TESTING /api/get_pending_assignments API')
    print('==========================================')
    
    # Get david_ops user
    david_user = User.query.filter_by(username='david_ops').first()
    print(f'User: {david_user.username} (ID: {david_user.id})')
    
    # Simulate API call
    assignments = IncidentAssignment.query.filter_by(
        assigned_to_id=david_user.id,
        assignment_status='pending'
    ).all()
    
    # Format like the actual API response
    assignment_data = []
    for assignment in assignments:
        assignment_data.append({
            'id': assignment.id,
            'incident_id': assignment.incident_id,
            'incident_title': assignment.incident_title,
            'incident_description': assignment.incident_description,
            'incident_priority': assignment.incident_priority,
            'assigned_by': assignment.assigned_by,
            'created_at': assignment.assigned_at.strftime('%Y-%m-%d %H:%M:%S') if assignment.assigned_at else None,
            'assignment_status': assignment.assignment_status
        })
    
    api_response = {
        'success': True,
        'assignments': assignment_data,
        'count': len(assignment_data)
    }
    
    print('📊 API Response:')
    print(json.dumps(api_response, indent=2, default=str))
    
    if len(assignment_data) > 0:
        print('')
        print('✅ API should return data - frontend issue likely')
        print('🎯 Check browser console for JavaScript errors')
    else:
        print('')
        print('❌ API returns empty - backend issue')
"

echo -e "\n🎯 FRONTEND DEBUGGING STEPS:"
echo "============================="
echo ""
echo "Since we know the user has assignments, the issue is likely:"
echo ""
echo "1. 🔍 JAVASCRIPT ERRORS (Most Likely)"
echo "   - Open F12 Developer Tools"
echo "   - Look in Console tab for errors"
echo "   - Check if loadDashboardNotifications() runs"
echo "   - Look for API call errors"
echo ""
echo "2. 🌐 API CALL ISSUES"
echo "   - Check Network tab in F12"
echo "   - Look for /api/get_pending_assignments request"
echo "   - Check response status and data"
echo ""
echo "3. 🎨 CSS/STYLING ISSUES"
echo "   - Notification panel might be hidden by CSS"
echo "   - Check if element exists in DOM"
echo ""
echo "4. 🔄 CACHING ISSUES"
echo "   - Try hard refresh (Ctrl+F5)"
echo "   - Clear browser cache"

echo -e "\n🛠️ QUICK FIX TEST:"
echo "=================="
echo ""
echo "In your browser console, try running this JavaScript:"
echo ""
echo "// Test if the notification panel exists"
echo "const panel = document.getElementById('incident-notifications-dashboard');"
echo "console.log('Panel element:', panel);"
echo ""
echo "// Test showing the panel manually"
echo "if (panel) {"
echo "    panel.style.display = 'block';"
echo "    document.getElementById('notifications-count').textContent = '1';"
echo "    console.log('Panel should now be visible');"
echo "} else {"
echo "    console.log('Panel element not found!');"
echo "}"
echo ""
echo "// Test the API call manually"
echo "fetch('/api/get_pending_assignments')"
echo "  .then(r => r.json())"
echo "  .then(d => console.log('API Response:', d));"

echo -e "\n🔧 COMMON SOLUTIONS:"
echo "===================="
echo ""
echo "1. JavaScript Error Fix:"
echo "   - If 'Plotly is not defined' error is blocking other JS"
echo "   - This might prevent notification script from running"
echo ""
echo "2. Element Not Found:"
echo "   - Check if notification panel HTML is properly included"
echo "   - Verify script runs after DOM is loaded"
echo ""
echo "3. API Authentication:"
echo "   - Ensure user session is maintained"
echo "   - Check if Flask-Login current_user works"

echo -e "\n📋 VERIFICATION STEPS:"
echo "====================="
echo ""
echo "Run these commands in browser console:"
echo "1. Check panel exists: document.getElementById('incident-notifications-dashboard')"
echo "2. Check API manually: fetch('/api/get_pending_assignments').then(r=>r.json()).then(console.log)"
echo "3. Test show panel: document.getElementById('incident-notifications-dashboard').style.display='block'"
echo ""
echo "If step 3 shows the panel, then API/JavaScript issue."
echo "If step 3 doesn't show anything, then HTML/CSS issue."
