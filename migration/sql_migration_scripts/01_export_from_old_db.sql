-- ============================================
-- EXPORT SCRIPT FOR OLD DATABASE
-- Run this on your OLD database server
-- ============================================

-- This script exports data to CSV format
-- Adjust paths as needed for your system

-- Create export directory (run from command line)
-- mkdir -p /tmp/shift_handover_export

-- ============================================
-- PHASE 1: Export Core Reference Data
-- ============================================

-- Export Accounts
\COPY (SELECT * FROM account ORDER BY id) TO '/tmp/shift_handover_export/account.csv' WITH CSV HEADER;

-- Export Teams
\COPY (SELECT * FROM team ORDER BY id) TO '/tmp/shift_handover_export/team.csv' WITH CSV HEADER;

-- Export Users (excluding sensitive password data if needed)
\COPY (SELECT * FROM "user" ORDER BY id) TO '/tmp/shift_handover_export/user.csv' WITH CSV HEADER;

-- Export Team Members
\COPY (SELECT * FROM team_member ORDER BY id) TO '/tmp/shift_handover_export/team_member.csv' WITH CSV HEADER;

-- Export User Team Memberships
\COPY (SELECT * FROM user_team_memberships ORDER BY id) TO '/tmp/shift_handover_export/user_team_memberships.csv' WITH CSV HEADER;

-- ============================================
-- PHASE 2: Export Shift Handover Data
-- ============================================

-- Export Shifts (Main Handover Records)
\COPY (SELECT * FROM shift ORDER BY id) TO '/tmp/shift_handover_export/shift.csv' WITH CSV HEADER;

-- Export Incidents
\COPY (SELECT * FROM incident ORDER BY id) TO '/tmp/shift_handover_export/incident.csv' WITH CSV HEADER;

-- Export Key Points
\COPY (SELECT * FROM shift_key_point ORDER BY id) TO '/tmp/shift_handover_export/shift_key_point.csv' WITH CSV HEADER;

-- Export Key Point Updates
\COPY (SELECT * FROM shift_key_point_update ORDER BY id) TO '/tmp/shift_handover_export/shift_key_point_update.csv' WITH CSV HEADER;

-- Export Change Info
\COPY (SELECT * FROM shift_change_info ORDER BY id) TO '/tmp/shift_handover_export/shift_change_info.csv' WITH CSV HEADER;

-- Export KB Updates
\COPY (SELECT * FROM shift_kb_update ORDER BY id) TO '/tmp/shift_handover_export/shift_kb_update.csv' WITH CSV HEADER;

-- Export Engineer Associations
\COPY (SELECT * FROM current_shift_engineers) TO '/tmp/shift_handover_export/current_shift_engineers.csv' WITH CSV HEADER;
\COPY (SELECT * FROM next_shift_engineers) TO '/tmp/shift_handover_export/next_shift_engineers.csv' WITH CSV HEADER;

-- ============================================
-- PHASE 3: Export Enhanced Handover Data
-- ============================================

-- Export Handover Requests (if table exists)
\COPY (SELECT * FROM handover_request ORDER BY id) TO '/tmp/shift_handover_export/handover_request.csv' WITH CSV HEADER;

-- Export Incident Assignments
\COPY (SELECT * FROM incident_assignment ORDER BY id) TO '/tmp/shift_handover_export/incident_assignment.csv' WITH CSV HEADER;

-- Export Incident Assignment Responses
\COPY (SELECT * FROM incident_assignment_response ORDER BY id) TO '/tmp/shift_handover_export/incident_assignment_response.csv' WITH CSV HEADER;

-- Export Handover Incident Response Logs
\COPY (SELECT * FROM handover_incident_response_log ORDER BY id) TO '/tmp/shift_handover_export/handover_incident_response_log.csv' WITH CSV HEADER;

-- Export Handover Responses
\COPY (SELECT * FROM handover_response ORDER BY id) TO '/tmp/shift_handover_export/handover_response.csv' WITH CSV HEADER;

-- Export Handover Notifications
\COPY (SELECT * FROM handover_notification ORDER BY id) TO '/tmp/shift_handover_export/handover_notification.csv' WITH CSV HEADER;

-- Export Handover Audit Logs
\COPY (SELECT * FROM handover_audit_log ORDER BY id) TO '/tmp/shift_handover_export/handover_audit_log.csv' WITH CSV HEADER;

-- ============================================
-- PHASE 4: Export Roster Data
-- ============================================

-- Export Shift Rosters
\COPY (SELECT * FROM shift_roster ORDER BY id) TO '/tmp/shift_handover_export/shift_roster.csv' WITH CSV HEADER;

-- ============================================
-- PHASE 5: Export Swap/Leave Data
-- ============================================

-- Export Shift Swap Requests
\COPY (SELECT * FROM shift_swap_request ORDER BY id) TO '/tmp/shift_handover_export/shift_swap_request.csv' WITH CSV HEADER;

-- Export Leave Requests
\COPY (SELECT * FROM leave_request ORDER BY id) TO '/tmp/shift_handover_export/leave_request.csv' WITH CSV HEADER;

-- ============================================
-- VERIFICATION: Get record counts
-- ============================================

SELECT 'account' as table_name, COUNT(*) as record_count FROM account
UNION ALL SELECT 'team', COUNT(*) FROM team
UNION ALL SELECT 'user', COUNT(*) FROM "user"
UNION ALL SELECT 'team_member', COUNT(*) FROM team_member
UNION ALL SELECT 'shift', COUNT(*) FROM shift
UNION ALL SELECT 'incident', COUNT(*) FROM incident
UNION ALL SELECT 'shift_key_point', COUNT(*) FROM shift_key_point
UNION ALL SELECT 'shift_key_point_update', COUNT(*) FROM shift_key_point_update
UNION ALL SELECT 'shift_change_info', COUNT(*) FROM shift_change_info
UNION ALL SELECT 'shift_kb_update', COUNT(*) FROM shift_kb_update
UNION ALL SELECT 'shift_roster', COUNT(*) FROM shift_roster
ORDER BY table_name;

-- ============================================
-- END OF EXPORT SCRIPT
-- ============================================
-- After running, copy /tmp/shift_handover_export/ 
-- to your new server for import







