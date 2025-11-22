#!/bin/bash
# Check Actual Database Schema in Docker
# Run this to see the real table structures

echo "🔍 CHECKING ACTUAL DATABASE SCHEMA"
echo "=================================="

echo "1. Checking incident_assignment table structure..."
docker-compose exec -T db mysql -u root -prootpassword shift_handover << 'EOF'
DESCRIBE incident_assignment;
EOF

echo -e "\n2. Checking handover_incident_response_log table structure..."
docker-compose exec -T db mysql -u root -prootpassword shift_handover << 'EOF'
DESCRIBE handover_incident_response_log;
EOF

echo -e "\n3. Checking root table structure..."
docker-compose exec -T db mysql -u root -prootpassword shift_handover << 'EOF'
DESCRIBE user;
EOF

echo -e "\n4. Checking all tables in database..."
docker-compose exec -T db mysql -u root -prootpassword shift_handover << 'EOF'
SHOW TABLES;
EOF

echo -e "\n5. Checking current data counts..."
docker-compose exec -T db mysql -u root -prootpassword shift_handover << 'EOF'
SELECT 'incident_assignment' as table_name, COUNT(*) as count FROM incident_assignment
UNION ALL
SELECT 'handover_incident_response_log', COUNT(*) FROM handover_incident_response_log
UNION ALL
SELECT 'user', COUNT(*) FROM user
UNION ALL
SELECT 'shift', COUNT(*) FROM shift;
EOF

echo -e "\n6. Sample data from existing tables..."
docker-compose exec -T db mysql -u root -prootpassword shift_handover << 'EOF'
SELECT 'Recent users:' as info;
SELECT id, username, email, role FROM user LIMIT 3;

SELECT 'Recent shifts:' as info;
SELECT id, date, current_shift_type, next_shift_type FROM shift ORDER BY date DESC LIMIT 3;
EOF

echo -e "\n🎯 This will show the actual table structures so we can create correct test data!"
