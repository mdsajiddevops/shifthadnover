#!/bin/bash

echo "User Management Debugging"
echo "========================"

# Check containers status
echo "1. Container Status:"
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | grep -E "(nginx|web|db)"
echo

# Check application logs for user management errors
echo "2. Recent Application Logs (User Management):"
docker logs shift-handover-web --tail=50 2>&1 | grep -i -E "(user|add|management|form|post|error|exception)" | tail -20
echo

# Test user management endpoint accessibility
echo "3. Testing User Management Endpoint:"
curl -I "http://localhost/user-management" 2>/dev/null | head -n 5
echo

# Check database for user management tables
echo "4. Database Table Structure:"
docker exec shift-handover-db mysql -u root -p$(docker exec shift-handover-db printenv MYSQL_ROOT_PASSWORD) shift_handover_db -e "
DESCRIBE users;
SELECT COUNT(*) as user_count FROM users;
SELECT COUNT(*) as account_count FROM accounts;
SELECT COUNT(*) as team_count FROM teams;" 2>/dev/null
echo

# Check for any JavaScript errors in browser console
echo "5. Testing Form Submission (simulated):"
echo "curl -X POST http://localhost/user-management -d 'action=add&username=testuser&password=testpass&role=user&account_id=1&first_name=Test&last_name=User'"
echo

# Check nginx logs for user management requests
echo "6. Nginx Access Logs (User Management):"
docker logs shift-handover-nginx --tail=20 2>&1 | grep -i "user-management" | tail -5
echo

echo "Debug complete. Common issues to check:"
echo "  1. Form not submitting - Check browser console for JavaScript errors"
echo "  2. No response after submit - Check Flask route handling"
echo "  3. Permission denied - Check user role and permissions"
echo "  4. Database errors - Check table structure and constraints"
echo "  5. Missing fields - Check form validation"
