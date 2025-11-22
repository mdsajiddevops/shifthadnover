-- Complete cleanup of all test data

-- First, let's see what we have
SELECT 'BEFORE CLEANUP:' as status;
SELECT COUNT(*) as incidents FROM incident;
SELECT COUNT(*) as assignments FROM incident_assignment;
SELECT COUNT(*) as logs FROM handover_incident_response_log;

-- Delete all records that appear to be test data
DELETE FROM handover_incident_response_log WHERE 1=1;
DELETE FROM incident_assignment WHERE 1=1;
DELETE FROM incident WHERE 1=1;

-- Verify everything is cleaned
SELECT 'AFTER CLEANUP:' as status;
SELECT COUNT(*) as incidents FROM incident;
SELECT COUNT(*) as assignments FROM incident_assignment;
SELECT COUNT(*) as logs FROM handover_incident_response_log;
SELECT COUNT(*) as key_points FROM shift_key_point;
