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
    DECLARE index_exists INT DEFAULT 0;
    
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
