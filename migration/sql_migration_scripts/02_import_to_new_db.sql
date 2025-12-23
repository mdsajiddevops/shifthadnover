-- ============================================
-- IMPORT SCRIPT FOR NEW DATABASE
-- Run this on your NEW database server
-- ============================================

-- IMPORTANT: Before importing, make sure:
-- 1. The export files are copied to the new server
-- 2. Tables exist in the new database (run Flask migrations first)
-- 3. Foreign key constraints might need to be temporarily disabled

-- Adjust the path to where you copied the export files
-- Example: /tmp/shift_handover_import/

-- ============================================
-- DISABLE FOREIGN KEY CHECKS (PostgreSQL)
-- ============================================
SET session_replication_role = 'replica';

-- ============================================
-- PHASE 1: Import Core Reference Data
-- Order matters due to foreign keys!
-- ============================================

-- Clear existing data (CAUTION: Only if needed!)
-- TRUNCATE account, team, "user", team_member CASCADE;

-- Import Accounts
\COPY account FROM '/tmp/shift_handover_import/account.csv' WITH CSV HEADER;

-- Import Teams
\COPY team FROM '/tmp/shift_handover_import/team.csv' WITH CSV HEADER;

-- Import Users
\COPY "user" FROM '/tmp/shift_handover_import/user.csv' WITH CSV HEADER;

-- Import Team Members
\COPY team_member FROM '/tmp/shift_handover_import/team_member.csv' WITH CSV HEADER;

-- Import User Team Memberships
\COPY user_team_memberships FROM '/tmp/shift_handover_import/user_team_memberships.csv' WITH CSV HEADER;

-- ============================================
-- PHASE 2: Import Shift Handover Data
-- ============================================

-- Import Shifts
\COPY shift FROM '/tmp/shift_handover_import/shift.csv' WITH CSV HEADER;

-- Import Incidents
\COPY incident FROM '/tmp/shift_handover_import/incident.csv' WITH CSV HEADER;

-- Import Key Points
\COPY shift_key_point FROM '/tmp/shift_handover_import/shift_key_point.csv' WITH CSV HEADER;

-- Import Key Point Updates
\COPY shift_key_point_update FROM '/tmp/shift_handover_import/shift_key_point_update.csv' WITH CSV HEADER;

-- Import Change Info
\COPY shift_change_info FROM '/tmp/shift_handover_import/shift_change_info.csv' WITH CSV HEADER;

-- Import KB Updates
\COPY shift_kb_update FROM '/tmp/shift_handover_import/shift_kb_update.csv' WITH CSV HEADER;

-- Import Engineer Associations
\COPY current_shift_engineers FROM '/tmp/shift_handover_import/current_shift_engineers.csv' WITH CSV HEADER;
\COPY next_shift_engineers FROM '/tmp/shift_handover_import/next_shift_engineers.csv' WITH CSV HEADER;

-- ============================================
-- PHASE 3: Import Enhanced Handover Data
-- ============================================

-- Import Handover Requests
\COPY handover_request FROM '/tmp/shift_handover_import/handover_request.csv' WITH CSV HEADER;

-- Import Incident Assignments
\COPY incident_assignment FROM '/tmp/shift_handover_import/incident_assignment.csv' WITH CSV HEADER;

-- Import Incident Assignment Responses
\COPY incident_assignment_response FROM '/tmp/shift_handover_import/incident_assignment_response.csv' WITH CSV HEADER;

-- Import Handover Incident Response Logs
\COPY handover_incident_response_log FROM '/tmp/shift_handover_import/handover_incident_response_log.csv' WITH CSV HEADER;

-- Import Handover Responses
\COPY handover_response FROM '/tmp/shift_handover_import/handover_response.csv' WITH CSV HEADER;

-- Import Handover Notifications
\COPY handover_notification FROM '/tmp/shift_handover_import/handover_notification.csv' WITH CSV HEADER;

-- Import Handover Audit Logs
\COPY handover_audit_log FROM '/tmp/shift_handover_import/handover_audit_log.csv' WITH CSV HEADER;

-- ============================================
-- PHASE 4: Import Roster Data
-- ============================================

\COPY shift_roster FROM '/tmp/shift_handover_import/shift_roster.csv' WITH CSV HEADER;

-- ============================================
-- PHASE 5: Import Swap/Leave Data
-- ============================================

\COPY shift_swap_request FROM '/tmp/shift_handover_import/shift_swap_request.csv' WITH CSV HEADER;
\COPY leave_request FROM '/tmp/shift_handover_import/leave_request.csv' WITH CSV HEADER;

-- ============================================
-- RE-ENABLE FOREIGN KEY CHECKS
-- ============================================
SET session_replication_role = 'origin';

-- ============================================
-- FIX SEQUENCES
-- After bulk import, sequences need to be updated
-- ============================================

-- Reset account sequence
SELECT setval('account_id_seq', (SELECT MAX(id) FROM account));

-- Reset team sequence
SELECT setval('team_id_seq', (SELECT MAX(id) FROM team));

-- Reset user sequence
SELECT setval('user_id_seq', (SELECT MAX(id) FROM "user"));

-- Reset team_member sequence
SELECT setval('team_member_id_seq', (SELECT MAX(id) FROM team_member));

-- Reset shift sequence
SELECT setval('shift_id_seq', (SELECT MAX(id) FROM shift));

-- Reset incident sequence
SELECT setval('incident_id_seq', (SELECT MAX(id) FROM incident));

-- Reset shift_key_point sequence
SELECT setval('shift_key_point_id_seq', (SELECT MAX(id) FROM shift_key_point));

-- Reset shift_key_point_update sequence
SELECT setval('shift_key_point_update_id_seq', (SELECT MAX(id) FROM shift_key_point_update));

-- Reset shift_change_info sequence
SELECT setval('shift_change_info_id_seq', (SELECT MAX(id) FROM shift_change_info));

-- Reset shift_kb_update sequence
SELECT setval('shift_kb_update_id_seq', (SELECT MAX(id) FROM shift_kb_update));

-- Reset shift_roster sequence
SELECT setval('shift_roster_id_seq', (SELECT MAX(id) FROM shift_roster));

-- Reset handover_request sequence (if exists)
SELECT setval('handover_request_id_seq', COALESCE((SELECT MAX(id) FROM handover_request), 1));

-- ============================================
-- VERIFICATION: Compare record counts
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
-- END OF IMPORT SCRIPT
-- ============================================




