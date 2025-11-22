#!/bin/bash
# Complete Notification System Diagnostic
# This script checks everything needed for notifications to work

echo "🔍 COMPLETE NOTIFICATION SYSTEM DIAGNOSTIC"
echo "==========================================="

echo "1. Checking database schema status..."
docker-compose exec -T db mysql -u root -prootpassword shift_handover << 'EOF'
SELECT 'incident_assignment table structure:' as info;
DESCRIBE incident_assignment;

SELECT 'handover_incident_response_log table structure:' as info;
DESCRIBE handover_incident_response_log;

SELECT 'Current data counts:' as info;
SELECT 'incident_assignment' as table_name, COUNT(*) as record_count FROM incident_assignment
UNION ALL
SELECT 'handover_incident_response_log' as table_name, COUNT(*) as record_count FROM handover_incident_response_log
UNION ALL
SELECT 'users' as table_name, COUNT(*) as record_count FROM users;
EOF

echo -e "\n2. Checking for actual incident assignment data..."
docker-compose exec -T db mysql -u root -prootpassword shift_handover << 'EOF'
SELECT 'Recent incident assignments (last 10):' as info;
SELECT 
    ia.id,
    ia.incident_id,
    ia.incident_title,
    ia.assigned_to_id,
    ia.assignment_status,
    ia.assigned_at,
    ia.handover_context
FROM incident_assignment ia
ORDER BY ia.assigned_at DESC
LIMIT 10;

SELECT 'Pending assignments for user ID 1:' as info;
SELECT 
    ia.id,
    ia.incident_id,
    ia.incident_title,
    ia.assignment_status,
    ia.assigned_at
FROM incident_assignment ia
WHERE ia.assigned_to_id = 1 AND ia.assignment_status = 'pending'
ORDER BY ia.assigned_at DESC;
EOF

echo -e "\n3. Checking handover response log data..."
docker-compose exec -T db mysql -u root -prootpassword shift_handover << 'EOF'
SELECT 'Recent handover response logs (last 10):' as info;
SELECT 
    hirl.id,
    hirl.incident_number,
    hirl.incident_title,
    hirl.assigned_by_name,
    hirl.accepted_by_name,
    hirl.assignment_status,
    hirl.assigned_at
FROM handover_incident_response_log hirl
ORDER BY hirl.assigned_at DESC
LIMIT 10;

SELECT 'Pending response logs:' as info;
SELECT 
    hirl.id,
    hirl.incident_number,
    hirl.incident_title,
    hirl.assignment_status,
    hirl.assigned_by_name
FROM handover_incident_response_log hirl
WHERE hirl.assignment_status = 'pending'
ORDER BY hirl.assigned_at DESC;
EOF

echo -e "\n4. Checking user data..."
docker-compose exec -T db mysql -u root -prootpassword shift_handover << 'EOF'
SELECT 'User accounts:' as info;
SELECT 
    id,
    username,
    email,
    role,
    account_id,
    team_id
FROM users
ORDER BY id
LIMIT 5;
EOF

echo -e "\n5. Testing notification queries that the app should use..."
docker-compose exec -T db mysql -u root -prootpassword shift_handover << 'EOF'
-- Query 1: User dashboard notifications (what users should see)
SELECT 'QUERY 1 - User Dashboard Notifications:' as query_info;
SELECT 
    ia.id as assignment_id,
    ia.incident_id,
    ia.incident_title,
    ia.incident_priority,
    ia.assignment_status,
    ia.handover_context,
    ia.assigned_at,
    u.username as assigned_to_username
FROM incident_assignment ia
LEFT JOIN users u ON ia.assigned_to_id = u.id
WHERE ia.assignment_status = 'pending'
ORDER BY ia.assigned_at DESC;

-- Query 2: Admin incident assignment report (what admin should see)
SELECT 'QUERY 2 - Admin Incident Assignment Report:' as query_info;
SELECT 
    hirl.id as log_id,
    hirl.incident_number,
    hirl.incident_title,
    hirl.assignment_status,
    hirl.assigned_by_name,
    hirl.accepted_by_name,
    hirl.assigned_at,
    hirl.responded_at
FROM handover_incident_response_log hirl
WHERE hirl.assignment_status IN ('pending', 'accepted', 'rejected')
ORDER BY hirl.assigned_at DESC;

-- Query 3: Combined view for debugging
SELECT 'QUERY 3 - Combined Assignment and Response Log:' as query_info;
SELECT 
    ia.id as assignment_id,
    ia.incident_id,
    ia.assignment_status as ia_status,
    hirl.id as response_log_id,
    hirl.assignment_status as hirl_status,
    ia.assigned_at as ia_assigned_at,
    hirl.assigned_at as hirl_assigned_at
FROM incident_assignment ia
LEFT JOIN handover_incident_response_log hirl ON ia.id = hirl.incident_assignment_id
WHERE ia.assignment_status = 'pending' OR hirl.assignment_status = 'pending'
ORDER BY ia.assigned_at DESC;
EOF

echo -e "\n6. Creating test data to verify notification system..."
docker-compose exec -T db mysql -u root -prootpassword shift_handover << 'EOF'
-- Create a test incident assignment
INSERT INTO incident_assignment (
    handover_request_id,
    incident_id,
    incident_title,
    incident_description,
    incident_priority,
    incident_status,
    assigned_to_id,
    assigned_by_id,
    assignment_notes,
    handover_context,
    assignment_status,
    assigned_at,
    account_id,
    team_id
) VALUES (
    1,
    'NOTIFICATION-TEST-001',
    'Notification System Test',
    'Testing if notifications appear in dashboard and admin reports',
    'High',
    'Open',
    1,
    2,
    'Test assignment for notification debugging',
    'This should appear in user dashboard notifications',
    'pending',
    NOW(),
    1,
    1
);

SELECT 'Test assignment created with ID:', LAST_INSERT_ID() as new_assignment_id;

-- Create corresponding response log entry
INSERT INTO handover_incident_response_log (
    response_date,
    response_datetime,
    from_shift_type,
    to_shift_type,
    assigned_by_id,
    assigned_by_name,
    accepted_by_id,
    accepted_by_name,
    incident_number,
    incident_title,
    incident_description,
    incident_priority,
    incident_type,
    incident_category,
    assignment_status,
    response_status,
    response_comments,
    assignment_notes,
    assigned_at,
    incident_assignment_id,
    account_id,
    team_id
) VALUES (
    CURDATE(),
    NOW(),
    'Day',
    'Evening',
    2,
    'admin',
    1,
    'testuser',
    'NOTIFICATION-TEST-001',
    'Notification System Test',
    'Testing if notifications appear in dashboard and admin reports',
    'High',
    'handover',
    'Application',
    'pending',
    'pending',
    'Test response log for notification debugging',
    'Test assignment for notification debugging',
    NOW(),
    (SELECT id FROM incident_assignment WHERE incident_id = 'NOTIFICATION-TEST-001'),
    1,
    1
);

SELECT 'Test response log created!' as status;
EOF

echo -e "\n7. Verifying test data appears in notification queries..."
docker-compose exec -T db mysql -u root -prootpassword shift_handover << 'EOF'
SELECT 'After creating test data - User notifications:' as info;
SELECT 
    ia.id,
    ia.incident_id,
    ia.incident_title,
    ia.assignment_status,
    ia.assigned_at
FROM incident_assignment ia
WHERE ia.assigned_to_id = 1 AND ia.assignment_status = 'pending'
ORDER BY ia.assigned_at DESC;

SELECT 'After creating test data - Admin reports:' as info;
SELECT 
    hirl.id,
    hirl.incident_number,
    hirl.incident_title,
    hirl.assignment_status,
    hirl.assigned_by_name
FROM handover_incident_response_log hirl
WHERE hirl.assignment_status = 'pending'
ORDER BY hirl.assigned_at DESC;
EOF

echo -e "\n8. Checking application routes and endpoints..."
echo "Checking if Flask app files exist and have the right functions..."

if [ -f "routes/handover.py" ]; then
    echo "✅ routes/handover.py exists"
    echo "Checking for notification-related functions..."
    grep -n "def.*notification\|def.*pending\|def.*dashboard" routes/handover.py || echo "❌ No notification functions found"
    grep -n "incident_assignment" routes/handover.py | head -5 || echo "❌ No incident_assignment references found"
else
    echo "❌ routes/handover.py NOT FOUND"
fi

if [ -f "app.py" ]; then
    echo "✅ app.py exists"
    echo "Checking for notification routes..."
    grep -n "@app.route.*notification\|@app.route.*dashboard\|@app.route.*pending" app.py || echo "❌ No notification routes found"
else
    echo "❌ app.py NOT FOUND"
fi

if [ -f "templates/dashboard.html" ]; then
    echo "✅ templates/dashboard.html exists"
    echo "Checking for notification display code..."
    grep -n "notification\|pending\|incident" templates/dashboard.html | head -3 || echo "❌ No notification display code found"
else
    echo "❌ templates/dashboard.html NOT FOUND"
fi

echo -e "\n9. Checking Docker container status..."
docker-compose ps

echo -e "\n10. Final recommendations..."
echo "🎯 NOTIFICATION TROUBLESHOOTING SUMMARY"
echo "======================================="
echo ""
echo "If notifications still don't appear, check these:"
echo ""
echo "1. 📱 Frontend Issues:"
echo "   - Check browser console for JavaScript errors"
echo "   - Verify AJAX calls to notification endpoints"
echo "   - Check if notification polling is working"
echo ""
echo "2. 🔗 Backend Issues:"
echo "   - Check Flask app logs: docker-compose logs web"
echo "   - Verify notification routes exist in app.py or routes/"
echo "   - Check if session user_id matches database user IDs"
echo ""
echo "3. 🔍 Database Issues:"
echo "   - Run: SELECT * FROM incident_assignment WHERE assigned_to_id = [YOUR_USER_ID]"
echo "   - Run: SELECT * FROM handover_incident_response_log WHERE assignment_status = 'pending'"
echo ""
echo "4. 🌐 Application Issues:"
echo "   - Clear browser cache and cookies"
echo "   - Check if user is properly logged in"
echo "   - Verify user permissions and role"
echo ""
echo "📧 Test Data Created: Look for 'NOTIFICATION-TEST-001' in your dashboard!"

# Clean up test data after a delay
echo -e "\n11. Cleaning up test data in 30 seconds..."
sleep 5
docker-compose exec -T db mysql -u root -prootpassword shift_handover << 'EOF'
DELETE FROM handover_incident_response_log WHERE incident_number = 'NOTIFICATION-TEST-001';
DELETE FROM incident_assignment WHERE incident_id = 'NOTIFICATION-TEST-001';
SELECT 'Test data cleaned up!' as cleanup_status;
EOF

echo -e "\n🚀 DIAGNOSTIC COMPLETE!"
echo "Check the output above and your web application dashboard."
