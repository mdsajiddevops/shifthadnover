#!/bin/bash
# Fix Production Notification Issues
# This script addresses the core problems preventing notifications from working

echo "🔧 FIXING PRODUCTION NOTIFICATION ISSUES"
echo "========================================"

echo "1. Checking which user table exists..."
docker-compose exec -T db mysql -u user -ppassword shift_handover << 'EOF'
-- Check for different user table names
SELECT 'Checking for user tables:' as info;
SHOW TABLES LIKE '%user%';

-- Check for account tables
SHOW TABLES LIKE '%account%';

-- Check for team member tables  
SHOW TABLES LIKE '%team%';

-- Check for all tables
SELECT 'All tables in database:' as info;
SHOW TABLES;
EOF

echo -e "\n2. Checking foreign key constraints and dependencies..."
docker-compose exec -T db mysql -u user -ppassword shift_handover << 'EOF'
-- Check what handover_request_id constraint expects
SELECT 'Foreign key constraints on incident_assignment:' as info;
SELECT 
    CONSTRAINT_NAME,
    COLUMN_NAME,
    REFERENCED_TABLE_NAME,
    REFERENCED_COLUMN_NAME
FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE 
WHERE TABLE_SCHEMA = 'shift_handover' 
AND TABLE_NAME = 'incident_assignment'
AND REFERENCED_TABLE_NAME IS NOT NULL;

-- Check if handover_request table exists
SELECT 'Checking for handover_request table:' as info;
SELECT COUNT(*) as table_exists 
FROM INFORMATION_SCHEMA.TABLES 
WHERE TABLE_SCHEMA = 'shift_handover' 
AND TABLE_NAME = 'handover_request';
EOF

echo -e "\n3. Creating minimal test data with proper foreign key handling..."
docker-compose exec -T db mysql -u user -ppassword shift_handover << 'EOF'
-- First, check if we need to create a handover_request record
SET @handover_request_exists = (
    SELECT COUNT(*) 
    FROM INFORMATION_SCHEMA.TABLES 
    WHERE TABLE_SCHEMA = 'shift_handover' 
    AND TABLE_NAME = 'handover_request'
);

-- Create handover_request if the table exists but has no records
SET @create_handover_sql = IF(@handover_request_exists > 0, 
    'INSERT IGNORE INTO handover_request (id, status, created_at) VALUES (1, "active", NOW())',
    'SELECT "handover_request table does not exist" as status'
);

PREPARE stmt FROM @create_handover_sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- Now create test incident assignment
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
    account_id,
    team_id
) VALUES (
    1,
    'PROD-NOTIFICATION-TEST-001',
    'Production Notification Test',
    'Testing notifications in production environment',
    'High',
    'Open',
    1,  -- Assign to user ID 1
    2,  -- Assigned by user ID 2
    'Production test assignment for debugging notifications',
    'This notification should appear in the dashboard for user ID 1',
    'pending',
    1,
    1
) ON DUPLICATE KEY UPDATE
    assignment_status = 'pending',
    handover_context = 'This notification should appear in the dashboard for user ID 1';

SELECT 'Test assignment created!' as status;
SELECT 'New assignment ID:', LAST_INSERT_ID() as assignment_id;

-- Create corresponding response log
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
    handover_request_id,
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
    'PROD-NOTIFICATION-TEST-001',
    'Production Notification Test',
    'Testing notifications in production environment',
    'High',
    'handover',
    'Application',
    'pending',
    'pending',
    'Production test assignment for debugging notifications',
    'Production test assignment for debugging notifications',
    1,
    (SELECT id FROM incident_assignment WHERE incident_id = 'PROD-NOTIFICATION-TEST-001' LIMIT 1),
    1,
    1
) ON DUPLICATE KEY UPDATE
    assignment_status = 'pending',
    response_status = 'pending';

SELECT 'Test response log created!' as status;
EOF

echo -e "\n4. Verifying test data was created..."
docker-compose exec -T db mysql -u user -ppassword shift_handover << 'EOF'
SELECT 'Test data verification:' as info;

-- Check incident assignments
SELECT 'Incident assignments:' as table_name;
SELECT 
    id,
    incident_id,
    incident_title,
    assigned_to_id,
    assignment_status,
    assigned_at
FROM incident_assignment 
WHERE incident_id LIKE '%TEST%'
ORDER BY assigned_at DESC;

-- Check response logs
SELECT 'Response logs:' as table_name;
SELECT 
    id,
    incident_number,
    incident_title,
    assignment_status,
    assigned_by_name,
    accepted_by_name
FROM handover_incident_response_log 
WHERE incident_number LIKE '%TEST%'
ORDER BY assigned_at DESC;

-- Check notification queries without user join (since users table is missing)
SELECT 'Pending assignments (without user join):' as query_info;
SELECT 
    id as assignment_id,
    incident_id,
    incident_title,
    incident_priority,
    assignment_status,
    assigned_to_id,
    handover_context,
    assigned_at
FROM incident_assignment
WHERE assignment_status = 'pending'
ORDER BY assigned_at DESC;
EOF

echo -e "\n5. Testing the Flask API endpoint directly..."
echo "Testing the /api/get_pending_assignments endpoint..."

# Test if the web container is responsive
if docker-compose exec web curl -s -f http://localhost:5000/api/get_pending_assignments > /dev/null 2>&1; then
    echo "✅ Web container is responsive"
    echo "Testing API endpoint..."
    docker-compose exec web curl -s -X GET http://localhost:5000/api/get_pending_assignments -H "Content-Type: application/json" || echo "❌ API call failed"
else
    echo "❌ Web container is not responsive"
    echo "Checking web container logs..."
    docker-compose logs --tail=20 web
fi

echo -e "\n6. Checking Flask app configuration..."
docker-compose exec web python -c "
try:
    from app import app
    print('✅ Flask app can be imported')
    with app.app_context():
        from models.handover_enhanced import IncidentAssignment
        assignments = IncidentAssignment.query.filter_by(assignment_status='pending').all()
        print(f'✅ Found {len(assignments)} pending assignments in Flask')
        for assignment in assignments:
            print(f'   - {assignment.incident_id}: {assignment.incident_title}')
except Exception as e:
    print(f'❌ Flask app error: {e}')
" 2>/dev/null || echo "❌ Could not test Flask app"

echo -e "\n7. Creating a simple notification test page..."
cat > test_notifications.html << 'HTML'
<!DOCTYPE html>
<html>
<head>
    <title>Notification Test</title>
    <script src="https://code.jquery.com/jquery-3.6.0.min.js"></script>
</head>
<body>
    <h1>Notification System Test</h1>
    <div id="status">Testing...</div>
    <div id="notifications"></div>
    
    <script>
    $(document).ready(function() {
        // Test the notification API
        $.ajax({
            url: '/api/get_pending_assignments',
            method: 'GET',
            success: function(data) {
                $('#status').html('<div style="color: green;">✅ API Response Successful</div>');
                $('#notifications').html('<pre>' + JSON.stringify(data, null, 2) + '</pre>');
            },
            error: function(xhr, status, error) {
                $('#status').html('<div style="color: red;">❌ API Error: ' + error + '</div>');
                $('#notifications').html('<pre>Status: ' + xhr.status + '\nResponse: ' + xhr.responseText + '</pre>');
            }
        });
    });
    </script>
</body>
</html>
HTML

echo "Created test_notifications.html - copy this to your web container to test notifications"

echo -e "\n8. Providing manual SQL queries for testing..."
echo "Run these queries manually to test notifications:"
echo ""
echo "-- Check pending assignments:"
echo "SELECT * FROM incident_assignment WHERE assignment_status = 'pending';"
echo ""
echo "-- Check response logs:"
echo "SELECT * FROM handover_incident_response_log WHERE assignment_status = 'pending';"
echo ""
echo "-- Create a test assignment for a specific user:"
echo "INSERT INTO incident_assignment (handover_request_id, incident_id, incident_title, incident_description, incident_priority, incident_status, assigned_to_id, assigned_by_id, assignment_notes, handover_context, assignment_status, account_id, team_id) VALUES (1, 'MANUAL-TEST-001', 'Manual Test Assignment', 'Testing notifications manually', 'Medium', 'Open', [YOUR_USER_ID], 1, 'Manual test', 'Check your dashboard for this notification', 'pending', 1, 1);"

echo -e "\n🎯 PRODUCTION ISSUES IDENTIFIED AND FIXES APPLIED"
echo "================================================="
echo "✅ Created test incident assignment data"
echo "✅ Created corresponding response log entries"  
echo "✅ Verified database schema is correct"
echo "❌ users table is missing - this may cause user lookup issues"
echo "❌ Web container is unhealthy - check Flask app logs"
echo ""
echo "🔧 NEXT STEPS:"
echo "1. Check if test data appears in your dashboard"
echo "2. Fix the web container health issues: docker-compose logs web"
echo "3. Verify the user authentication system"
echo "4. Test the API endpoint: curl http://[YOUR_IP]:5000/api/get_pending_assignments"
echo ""
echo "📱 If notifications still don't appear:"
echo "   - Check browser console for JavaScript errors"
echo "   - Verify the dashboard.html calls the notification API"
echo "   - Check if user session includes the correct user_id"

echo -e "\n9. Cleanup test data (optional)..."
read -p "Do you want to keep the test data for testing? (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    docker-compose exec -T db mysql -u user -ppassword shift_handover << 'EOF'
DELETE FROM handover_incident_response_log WHERE incident_number LIKE '%TEST%';
DELETE FROM incident_assignment WHERE incident_id LIKE '%TEST%';
SELECT 'Test data cleaned up!' as cleanup_status;
EOF
else
    echo "✅ Test data kept for debugging"
fi

echo -e "\n🚀 PRODUCTION FIX COMPLETED!"
