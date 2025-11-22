-- Final verification that all test data is removed

-- Check handover_incident_response_log one more time
SELECT 'HANDOVER INCIDENT RESPONSE LOGS:' as info;
SELECT id, incident_title, incident_number, assigned_by_name, accepted_by_name, response_status, created_at
FROM handover_incident_response_log 
ORDER BY created_at DESC;

-- Check for any remaining incidents
SELECT 'REMAINING INCIDENTS:' as info;
SELECT id, title, status, priority, description 
FROM incident 
ORDER BY id DESC;

-- Check for any remaining incident assignments
SELECT 'REMAINING INCIDENT ASSIGNMENTS:' as info;
SELECT id, incident_title, assigned_by_id, assignment_status, created_at
FROM incident_assignment
ORDER BY created_at DESC;

-- Check key points (should be empty now)
SELECT 'KEY POINTS (SHOULD BE EMPTY):' as info;
SELECT COUNT(*) as total_key_points FROM shift_key_point;

-- Final summary counts
SELECT 'FINAL PRODUCTION STATE:' as info;
SELECT 
  (SELECT COUNT(*) FROM incident) as incidents,
  (SELECT COUNT(*) FROM incident_assignment) as assignments,
  (SELECT COUNT(*) FROM handover_incident_response_log) as response_logs,
  (SELECT COUNT(*) FROM shift_key_point) as key_points;
