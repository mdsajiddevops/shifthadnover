#!/bin/bash
# Create Correct Test Data Based on Actual Schema
# This uses the original schema without enhanced columns

echo "🧪 CREATING TEST DATA (CORRECTED FOR ACTUAL SCHEMA)"
echo "=================================================="

echo "1. Creating test incident assignment (using actual schema)..."
docker-compose exec -T db mysql -u root -prootpassword shift_handover << 'EOF'
-- Check current user and shift data first
SELECT 'Available users:' as info;
SELECT id, username, email, role FROM user WHERE role IN ('user', 'team_admin') LIMIT 3;

SELECT 'Available shifts:' as info;  
SELECT id, date, current_shift_type, next_shift_type FROM shift ORDER BY date DESC LIMIT 3;

-- Create test data using actual schema
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
    account_id,
    team_id
) VALUES (
    1,                                    -- handover_request_id (using 1 as default)
    'CORRECTED-TEST-001',                 -- incident_id
    'Production Test - Corrected Schema', -- incident_title
    'Test using actual database schema',  -- incident_description
    'High',                               -- incident_priority
    'Open',                               -- incident_status
    1,                                    -- assigned_to_id (first user)
    1,                                    -- assigned_by_id (first user)
    'Created with correct schema',        -- assignment_notes
    1,                                    -- account_id
    1                                     -- team_id
);

SELECT 'Test incident assignment created!' as status;
SELECT COUNT(*) as assignments_count FROM incident_assignment;
EOF

echo -e "\n2. Creating handover_incident_response_log entry..."
docker-compose exec -T db mysql -u root -prootpassword shift_handover << 'EOF'
-- First, check what columns exist in handover_incident_response_log
DESCRIBE handover_incident_response_log;
EOF

echo -e "\n3. Verifying test data creation..."
docker-compose exec -T db mysql -u root -prootpassword shift_handover << 'EOF'
SELECT 'Current incident assignments:' as info;
SELECT id, incident_id, incident_title, incident_priority, assigned_to_id, assigned_by_id, created_at
FROM incident_assignment 
ORDER BY created_at DESC 
LIMIT 5;

SELECT 'Total counts:' as info;
SELECT 'incident_assignment' as table_name, COUNT(*) as count FROM incident_assignment
UNION ALL  
SELECT 'handover_incident_response_log', COUNT(*) FROM handover_incident_response_log;
EOF

echo -e "\n4. Testing notification queries..."
docker-compose exec -T db mysql -u root -prootpassword shift_handover << 'EOF'
-- Query that would be used for user notifications
SELECT 'User notification query (user_id=1):' as info;
SELECT ia.id, ia.incident_title, ia.incident_priority, ia.assigned_to_id, ia.created_at
FROM incident_assignment ia
WHERE ia.assigned_to_id = 1
ORDER BY ia.created_at DESC;

-- Query for admin logs
SELECT 'All recent assignments:' as info;
SELECT ia.id, ia.incident_title, ia.incident_priority, u.username as assigned_to
FROM incident_assignment ia
LEFT JOIN user u ON ia.assigned_to_id = u.id
ORDER BY ia.created_at DESC
LIMIT 5;
EOF

echo -e "\n5. Cleanup command (run separately if needed):"
echo "docker-compose exec -T db mysql -u user -ppassword shift_handover -e \"DELETE FROM incident_assignment WHERE incident_id = 'CORRECTED-TEST-001';\""

echo -e "\n🎯 Test completed! Check the results above."
echo "If incident_assignment count increased, the schema is working!"
