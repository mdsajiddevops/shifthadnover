-- Performance Indexes Migration Script
-- Phase 1: Zero-Risk Quick Wins
-- Run this on your local MySQL database

-- Use stored procedure to safely add indexes

DELIMITER //

DROP PROCEDURE IF EXISTS add_index_if_not_exists //

CREATE PROCEDURE add_index_if_not_exists(
    IN p_table_name VARCHAR(128),
    IN p_index_name VARCHAR(128),
    IN p_index_def VARCHAR(512)
)
BEGIN
    DECLARE table_exists INT DEFAULT 0;
    DECLARE index_exists INT DEFAULT 0;

    -- First check if table exists
    SELECT COUNT(*) INTO table_exists
    FROM information_schema.TABLES
    WHERE TABLE_SCHEMA = DATABASE()
    AND TABLE_NAME = p_table_name;

    IF table_exists = 0 THEN
        SELECT CONCAT('Table does not exist: ', p_table_name, ' - skipping index ', p_index_name) AS result;
    ELSE
        -- Check if index already exists
        SELECT COUNT(*) INTO index_exists
        FROM information_schema.STATISTICS
        WHERE TABLE_SCHEMA = DATABASE()
        AND TABLE_NAME = p_table_name
        AND INDEX_NAME = p_index_name;

        IF index_exists = 0 THEN
            SET @sql = CONCAT('CREATE INDEX ', p_index_name, ' ON ', p_table_name, '(', p_index_def, ')');
            PREPARE stmt FROM @sql;
            EXECUTE stmt;
            DEALLOCATE PREPARE stmt;
            SELECT CONCAT('Created index: ', p_index_name, ' on ', p_table_name) AS result;
        ELSE
            SELECT CONCAT('Index already exists: ', p_index_name, ' on ', p_table_name) AS result;
        END IF;
    END IF;
END //

DELIMITER ;

-- =============================================================
-- 1. Shift table indexes (heavily queried for dashboard, reports)
-- =============================================================
CALL add_index_if_not_exists('shift', 'idx_shift_date', 'date');
CALL add_index_if_not_exists('shift', 'idx_shift_team_date', 'team_id, date');
CALL add_index_if_not_exists('shift', 'idx_shift_status', 'status');
CALL add_index_if_not_exists('shift', 'idx_shift_account_team', 'account_id, team_id');

-- =============================================================
-- 2. ShiftKeyPoint indexes (key points page, dashboard, handover form)
-- =============================================================
CALL add_index_if_not_exists('shift_key_point', 'idx_keypoint_status', 'status');
CALL add_index_if_not_exists('shift_key_point', 'idx_keypoint_team_status', 'team_id, status');
CALL add_index_if_not_exists('shift_key_point', 'idx_keypoint_shift', 'shift_id');
CALL add_index_if_not_exists('shift_key_point', 'idx_keypoint_account_team', 'account_id, team_id');

-- =============================================================
-- 3. Incident table indexes
-- =============================================================
CALL add_index_if_not_exists('incident', 'idx_incident_shift', 'shift_id');
CALL add_index_if_not_exists('incident', 'idx_incident_type', 'type');
CALL add_index_if_not_exists('incident', 'idx_incident_team_type', 'team_id, type');

-- =============================================================
-- 4. ShiftRoster indexes (roster page, engineer lookups)
-- =============================================================
CALL add_index_if_not_exists('shift_roster', 'idx_roster_date_team', 'date, team_id');
CALL add_index_if_not_exists('shift_roster', 'idx_roster_shift_code', 'shift_code');
CALL add_index_if_not_exists('shift_roster', 'idx_roster_member', 'team_member_id');

-- =============================================================
-- 5. TeamMember indexes
-- =============================================================
CALL add_index_if_not_exists('team_member', 'idx_member_team', 'team_id');
CALL add_index_if_not_exists('team_member', 'idx_member_account', 'account_id');
CALL add_index_if_not_exists('team_member', 'idx_member_team_active', 'team_id, is_active');

-- =============================================================
-- 6. User table indexes
-- =============================================================
CALL add_index_if_not_exists('user', 'idx_user_activity', 'last_activity');
CALL add_index_if_not_exists('user', 'idx_user_account_active', 'account_id, is_active');

-- =============================================================
-- 7. ShiftChangeInfo indexes
-- =============================================================
CALL add_index_if_not_exists('shift_change_info', 'idx_changeinfo_shift', 'shift_id');
CALL add_index_if_not_exists('shift_change_info', 'idx_changeinfo_status', 'status');
CALL add_index_if_not_exists('shift_change_info', 'idx_changeinfo_team', 'team_id');

-- =============================================================
-- 8. ShiftKBUpdate indexes
-- =============================================================
CALL add_index_if_not_exists('shift_kb_update', 'idx_kbupdate_shift', 'shift_id');
CALL add_index_if_not_exists('shift_kb_update', 'idx_kbupdate_status', 'status');
CALL add_index_if_not_exists('shift_kb_update', 'idx_kbupdate_team', 'team_id');

-- =============================================================
-- 9. Association tables indexes (engineer relationships)
-- =============================================================
CALL add_index_if_not_exists('current_shift_engineers', 'idx_current_engineers_shift', 'shift_id');
CALL add_index_if_not_exists('current_shift_engineers', 'idx_current_engineers_member', 'team_member_id');
CALL add_index_if_not_exists('next_shift_engineers', 'idx_next_engineers_shift', 'shift_id');
CALL add_index_if_not_exists('next_shift_engineers', 'idx_next_engineers_member', 'team_member_id');

-- =============================================================
-- 10. EmailDeliveryLog indexes (email monitoring)
-- =============================================================
CALL add_index_if_not_exists('email_delivery_log', 'idx_email_log_status', 'status');
CALL add_index_if_not_exists('email_delivery_log', 'idx_email_log_sent_at', 'sent_at');
CALL add_index_if_not_exists('email_delivery_log', 'idx_email_log_team_date', 'team_id, created_at');

-- =============================================================
-- 11. HandoverRequest indexes (enhanced workflow)
-- Note: handover_request uses shift_date, not shift_id
-- =============================================================
CALL add_index_if_not_exists('handover_request', 'idx_handover_req_status', 'status');
CALL add_index_if_not_exists('handover_request', 'idx_handover_req_team', 'team_id, status');
CALL add_index_if_not_exists('handover_request', 'idx_handover_req_date', 'shift_date');
CALL add_index_if_not_exists('handover_request', 'idx_handover_req_created', 'created_at');

-- =============================================================
-- 12. IncidentAssignment indexes
-- Note: uses assignment_status, not status
-- =============================================================
CALL add_index_if_not_exists('incident_assignment', 'idx_inc_assign_request', 'handover_request_id');
CALL add_index_if_not_exists('incident_assignment', 'idx_inc_assign_user', 'assigned_to_id, assignment_status');

-- =============================================================
-- 13. HandoverNotification indexes (unread notifications)
-- Note: uses recipient_id, not user_id
-- =============================================================
CALL add_index_if_not_exists('handover_notification', 'idx_notif_user_read', 'recipient_id, is_read');
CALL add_index_if_not_exists('handover_notification', 'idx_notif_created', 'created_at');

-- =============================================================
-- 14. ProblemTicket indexes
-- =============================================================
CALL add_index_if_not_exists('problem_ticket', 'idx_problem_team_status', 'team_id, status');
CALL add_index_if_not_exists('problem_ticket', 'idx_problem_priority', 'priority, status');
CALL add_index_if_not_exists('problem_ticket', 'idx_problem_owner', 'owner_id');

-- =============================================================
-- 15. ProblemTask indexes
-- =============================================================
CALL add_index_if_not_exists('problem_task', 'idx_ptask_problem', 'problem_id');
CALL add_index_if_not_exists('problem_task', 'idx_ptask_status', 'status');
CALL add_index_if_not_exists('problem_task', 'idx_ptask_due', 'due_date, status');
CALL add_index_if_not_exists('problem_task', 'idx_ptask_assigned', 'assigned_to_id');

-- =============================================================
-- 16. ServiceNowIncident indexes
-- Note: table is servicenow_incidents (plural), uses updated_on
-- =============================================================
CALL add_index_if_not_exists('servicenow_incidents', 'idx_snow_team_state', 'team_id, state');
CALL add_index_if_not_exists('servicenow_incidents', 'idx_snow_priority', 'priority, state');
CALL add_index_if_not_exists('servicenow_incidents', 'idx_snow_updated', 'updated_on');

-- =============================================================
-- 17. CheckInLog indexes
-- =============================================================
CALL add_index_if_not_exists('checkin_log', 'idx_checkin_member', 'team_member_id');
CALL add_index_if_not_exists('checkin_log', 'idx_checkin_time', 'checkin_time');

-- =============================================================
-- 18. UserTeamMembership indexes (already has some, add more)
-- =============================================================
CALL add_index_if_not_exists('user_team_memberships', 'idx_membership_account', 'account_id, is_active');

-- =============================================================
-- 19. TeamFeatureConfig indexes
-- Note: uses scope_type, scope_id, is_enabled (not team_id, is_active)
-- =============================================================
CALL add_index_if_not_exists('team_feature_config', 'idx_feature_scope', 'scope_type, scope_id');
CALL add_index_if_not_exists('team_feature_config', 'idx_feature_key', 'feature_key, is_enabled');

-- =============================================================
-- 20. TeamEmailConfig indexes
-- =============================================================
CALL add_index_if_not_exists('team_email_config', 'idx_email_config_team', 'team_id, is_active');
CALL add_index_if_not_exists('team_email_config', 'idx_email_config_account', 'account_id, is_active');

-- =============================================================
-- 21. AuditLog indexes (for compliance queries)
-- Note: uses timestamp, not created_at
-- =============================================================
CALL add_index_if_not_exists('audit_log', 'idx_audit_user', 'user_id');
CALL add_index_if_not_exists('audit_log', 'idx_audit_action', 'action');
CALL add_index_if_not_exists('audit_log', 'idx_audit_timestamp', 'timestamp');

-- =============================================================
-- 22. SecretAuditLog indexes
-- =============================================================
CALL add_index_if_not_exists('secret_audit_log', 'idx_secret_audit_key', 'secret_key');
CALL add_index_if_not_exists('secret_audit_log', 'idx_secret_audit_time', 'timestamp');

-- =============================================================
-- Cleanup stored procedure
-- =============================================================
DROP PROCEDURE IF EXISTS add_index_if_not_exists;

-- =============================================================
-- Verify indexes were created
-- =============================================================
SELECT 
    TABLE_NAME,
    INDEX_NAME,
    GROUP_CONCAT(COLUMN_NAME ORDER BY SEQ_IN_INDEX) AS COLUMNS
FROM information_schema.STATISTICS 
WHERE TABLE_SCHEMA = DATABASE()
AND INDEX_NAME LIKE 'idx_%'
GROUP BY TABLE_NAME, INDEX_NAME
ORDER BY TABLE_NAME, INDEX_NAME;
