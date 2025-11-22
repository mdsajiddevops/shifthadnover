#!/bin/bash
# Quick Auto-Increment Fix - Run this AFTER schema migration
# This script only fixes the auto-increment issue with proper FK handling

echo "🔧 QUICK AUTO-INCREMENT FIX"
echo "============================"

echo "1. Current status check..."
docker-compose exec -T db mysql -u root -prootpassword shift_handover << 'EOF'
SELECT 'Current id column status:' as info;
SELECT COLUMN_NAME, IS_NULLABLE, COLUMN_DEFAULT, EXTRA
FROM INFORMATION_SCHEMA.COLUMNS 
WHERE TABLE_SCHEMA = 'shift_handover' 
AND TABLE_NAME = 'incident_assignment' 
AND COLUMN_NAME = 'id';

SELECT 'Foreign key constraints to handle:' as info;
SELECT 
    CONSTRAINT_NAME,
    TABLE_NAME,
    COLUMN_NAME
FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE 
WHERE REFERENCED_TABLE_SCHEMA = 'shift_handover' 
AND REFERENCED_TABLE_NAME = 'incident_assignment' 
AND REFERENCED_COLUMN_NAME = 'id';
EOF

echo -e "\n2. Dropping ALL foreign key constraints..."
docker-compose exec -T db mysql -u root -prootpassword shift_handover << 'EOF'
-- Drop incident_assignment_response FK
DROP FOREIGN KEY IF EXISTS incident_assignment_response_ibfk_1;
ALTER TABLE incident_assignment_response DROP FOREIGN KEY incident_assignment_response_ibfk_1;

-- Drop handover_audit_log FK  
ALTER TABLE handover_audit_log DROP FOREIGN KEY handover_audit_log_ibfk_2;

SELECT 'Foreign key constraints dropped!' as status;
EOF

echo -e "\n3. Adding AUTO_INCREMENT to id column..."
docker-compose exec -T db mysql -u root -prootpassword shift_handover << 'EOF'
ALTER TABLE incident_assignment MODIFY COLUMN id int NOT NULL AUTO_INCREMENT;

SELECT 'AUTO_INCREMENT added successfully!' as status;

-- Verify the change
SELECT COLUMN_NAME, IS_NULLABLE, COLUMN_DEFAULT, EXTRA
FROM INFORMATION_SCHEMA.COLUMNS 
WHERE TABLE_SCHEMA = 'shift_handover' 
AND TABLE_NAME = 'incident_assignment' 
AND COLUMN_NAME = 'id';
EOF

echo -e "\n4. Recreating foreign key constraints..."
docker-compose exec -T db mysql -u root -prootpassword shift_handover << 'EOF'
-- Recreate incident_assignment_response FK
ALTER TABLE incident_assignment_response 
ADD CONSTRAINT incident_assignment_response_ibfk_1 
FOREIGN KEY (incident_assignment_id) 
REFERENCES incident_assignment (id) 
ON DELETE CASCADE ON UPDATE CASCADE;

-- Recreate handover_audit_log FK
ALTER TABLE handover_audit_log 
ADD CONSTRAINT handover_audit_log_ibfk_2 
FOREIGN KEY (incident_assignment_id) 
REFERENCES incident_assignment (id) 
ON DELETE SET NULL ON UPDATE CASCADE;

SELECT 'Foreign key constraints recreated!' as status;
EOF

echo -e "\n5. Testing auto-increment functionality..."
docker-compose exec -T db mysql -u root -prootpassword shift_handover << 'EOF'
-- Test INSERT without specifying id
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
    'AUTO-INC-QUICK-TEST',
    'Quick Auto-Increment Test',
    'Testing auto-increment works without specifying id',
    'Medium',
    'Open',
    1,
    1,
    'Quick test of auto-increment functionality',
    'Auto-increment test after FK fix',
    'pending',
    1,
    1
);

SELECT 'Test record created successfully!' as status;
SELECT 'New ID assigned:', LAST_INSERT_ID() as new_id;

-- Show the test record
SELECT id, incident_id, incident_title, assignment_status 
FROM incident_assignment 
WHERE incident_id = 'AUTO-INC-QUICK-TEST';

-- Clean up
DELETE FROM incident_assignment WHERE incident_id = 'AUTO-INC-QUICK-TEST';
SELECT 'Test data cleaned up!' as cleanup;
EOF

echo -e "\n🎯 AUTO-INCREMENT FIX COMPLETED!"
echo "================================="
echo "✅ Foreign key constraints handled"
echo "✅ AUTO_INCREMENT property added"
echo "✅ INSERT operations now work without specifying id"
echo ""
echo "🚀 Try creating a handover in your app now!"
