#!/bin/bash
# Quick Docker Database Test
# One-command test for your Docker MySQL setup

echo "🐳 QUICK DOCKER DATABASE TEST"
echo "=============================="

echo "1. Checking Docker containers..."
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

echo -e "\n2. Testing MySQL connectivity and checking schema..."
echo "Connecting to MySQL container..."

# Test MySQL connection and get incident data
docker-compose exec -T db mysql -u root -prootpassword shift_handover << 'EOF'
SELECT '=== DATABASE SCHEMA CHECK ===' as info;

-- Check if enhanced columns exist
SELECT 'Checking incident_assignment columns:' as info;
DESCRIBE incident_assignment;

SELECT 'Table Counts:' as info;
SELECT 'incident_assignment' as table_name, COUNT(*) as records FROM incident_assignment
UNION ALL
SELECT 'handover_incident_response_log', COUNT(*) FROM handover_incident_response_log  
UNION ALL
SELECT 'user', COUNT(*) FROM user
UNION ALL  
SELECT 'shift', COUNT(*) FROM shift
UNION ALL
SELECT 'incident', COUNT(*) FROM incident;

SELECT '=== INCIDENT NOTIFICATION DIAGNOSIS ===' as info;
SELECT 
    CASE 
        WHEN (SELECT COUNT(*) FROM incident_assignment) = 0 AND 
             (SELECT COUNT(*) FROM handover_incident_response_log) = 0 
        THEN 'NO INCIDENT ASSIGNMENTS FOUND - This explains missing notifications!'
        ELSE 'Incident assignments exist - check notification queries'
    END as diagnosis;

SELECT '=== RECENT SHIFTS ===' as info;
SELECT id, date, current_shift_type, next_shift_type, status
FROM shift 
ORDER BY date DESC 
LIMIT 3;

SELECT '=== USERS WHO CAN RECEIVE NOTIFICATIONS ===' as info;
SELECT id, username, email, role, account_id, team_id
FROM user 
WHERE role IN ('user', 'team_admin') 
AND email IS NOT NULL 
AND email != ''
LIMIT 3;

SELECT 'Test completed!' as status;
EOF

echo -e "\n3. Testing Flask in app container..."
docker-compose exec web python3 -c "
try:
    import flask, mysql.connector
    print('✅ Flask and MySQL connector available')
    from app import create_app
    print('✅ App import successful')
except Exception as e:
    print(f'❌ Error: {e}')
" 2>/dev/null || echo "⚠️  Flask/app import issues detected"

echo -e "\n🎯 SUMMARY:"
echo "==========="
echo "If incident tables show 0 records, that's the root cause!"
echo "Handovers are being created but not calling the incident assignment function."
echo ""
echo "Next steps:"
echo "1. If MySQL works but Flask fails: Fix Python environment in container"
echo "2. If both work: Check handover creation logs for errors"
echo "3. Create test data manually to verify notification system works"
