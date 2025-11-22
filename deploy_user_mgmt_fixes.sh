#!/bin/bash

echo "Deploying User Management Fixes"
echo "==============================="

# Copy test files to container
echo "1. Copying test files..."
docker cp test_user_form.html shift-handover-web:/app/
docker cp user_management_js_fix.html shift-handover-web:/app/

# Make debug script executable and copy
chmod +x debug_user_management.sh

echo "2. Files deployed successfully!"
echo
echo "Testing options:"
echo "  1. Run debug script: ./debug_user_management.sh"
echo "  2. Access test form: http://35.200.202.18/test-add-user"
echo "  3. Check browser console for JavaScript errors"
echo "  4. Review application logs: docker logs shift-handover-web"
echo
echo "Common fixes:"
echo "  - Check if JavaScript is enabled in browser"
echo "  - Verify form action URL is correct"
echo "  - Ensure user has proper permissions"
echo "  - Check database connectivity"
