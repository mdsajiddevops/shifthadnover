-- Clean up remaining test incidents and related data

-- Delete remaining ServiceNow test incidents and App-5 incident
DELETE FROM handover_incident_response_log 
WHERE incident_title LIKE '%ServiceNow%' OR incident_title LIKE '%App-5%';

DELETE FROM incident_assignment 
WHERE incident_title LIKE '%ServiceNow%' OR incident_title LIKE '%App-5%';

DELETE FROM incident 
WHERE title LIKE '%ServiceNow%' OR title LIKE '%App-5%' OR title LIKE '%INC%';

-- Final verification
SELECT 'FINAL CLEANUP COMPLETE' as status;
SELECT 
  (SELECT COUNT(*) FROM incident) as total_incidents,
  (SELECT COUNT(*) FROM incident_assignment) as total_assignments,
  (SELECT COUNT(*) FROM handover_incident_response_log) as total_response_logs,
  (SELECT COUNT(*) FROM shift_key_point) as total_key_points;
