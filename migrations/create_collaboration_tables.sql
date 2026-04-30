-- Create collaborative handover tables if they don't exist
-- Run this script to enable real-time collaboration features

-- Create handover_session table
CREATE TABLE IF NOT EXISTS handover_session (
    id INT AUTO_INCREMENT PRIMARY KEY,
    shift_id INT NOT NULL,
    user_id INT NOT NULL,
    session_token VARCHAR(64) NOT NULL,
    started_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    last_heartbeat DATETIME DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    current_section VARCHAR(64) NULL,
    current_item_id VARCHAR(64) NULL,
    FOREIGN KEY (shift_id) REFERENCES shift(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES user(id) ON DELETE CASCADE,
    UNIQUE INDEX ix_handover_session_session_token (session_token),
    INDEX ix_handover_session_shift_id (shift_id),
    INDEX ix_handover_session_last_heartbeat (last_heartbeat),
    INDEX ix_handover_session_is_active (is_active),
    INDEX idx_active_sessions (shift_id, is_active),
    INDEX idx_session_heartbeat (is_active, last_heartbeat)
);

-- Create section_lock table
CREATE TABLE IF NOT EXISTS section_lock (
    id INT AUTO_INCREMENT PRIMARY KEY,
    shift_id INT NOT NULL,
    user_id INT NOT NULL,
    section_type VARCHAR(32) NOT NULL,
    item_id VARCHAR(64) NOT NULL,
    locked_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    expires_at DATETIME NOT NULL,
    FOREIGN KEY (shift_id) REFERENCES shift(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES user(id) ON DELETE CASCADE,
    INDEX ix_section_lock_shift_id (shift_id),
    INDEX idx_lock_expiry (expires_at),
    UNIQUE INDEX idx_section_lock_unique (shift_id, section_type, item_id)
);

-- Create handover_change table
CREATE TABLE IF NOT EXISTS handover_change (
    id INT AUTO_INCREMENT PRIMARY KEY,
    shift_id INT NOT NULL,
    user_id INT NOT NULL,
    change_type VARCHAR(32) NOT NULL,
    section_type VARCHAR(32) NOT NULL,
    item_id VARCHAR(64) NULL,
    field_name VARCHAR(64) NULL,
    old_value TEXT NULL,
    new_value TEXT NULL,
    changed_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    version INT DEFAULT 1,
    is_conflict BOOLEAN DEFAULT FALSE,
    conflict_resolved BOOLEAN NULL,
    resolution_type VARCHAR(32) NULL,
    FOREIGN KEY (shift_id) REFERENCES shift(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES user(id) ON DELETE CASCADE,
    INDEX ix_handover_change_shift_id (shift_id),
    INDEX ix_handover_change_changed_at (changed_at),
    INDEX idx_changes_by_shift (shift_id, changed_at),
    INDEX idx_changes_by_section (shift_id, section_type, item_id)
);

-- Create draft_incident table
CREATE TABLE IF NOT EXISTS draft_incident (
    id INT AUTO_INCREMENT PRIMARY KEY,
    shift_id INT NOT NULL,
    temp_id VARCHAR(64) NOT NULL,
    incident_number VARCHAR(64) NULL,
    description TEXT NULL,
    status VARCHAR(32) NULL,
    priority VARCHAR(32) NULL,
    assigned_to VARCHAR(128) NULL,
    notes TEXT NULL,
    created_by_user_id INT NOT NULL,
    last_modified_by_user_id INT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    modified_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    version INT DEFAULT 1,
    is_deleted BOOLEAN DEFAULT FALSE,
    FOREIGN KEY (shift_id) REFERENCES shift(id) ON DELETE CASCADE,
    FOREIGN KEY (created_by_user_id) REFERENCES user(id),
    FOREIGN KEY (last_modified_by_user_id) REFERENCES user(id),
    INDEX ix_draft_incident_shift_id (shift_id),
    INDEX ix_draft_incident_temp_id (temp_id),
    INDEX idx_draft_incidents (shift_id, is_deleted)
);

-- Create draft_key_point table
CREATE TABLE IF NOT EXISTS draft_key_point (
    id INT AUTO_INCREMENT PRIMARY KEY,
    shift_id INT NOT NULL,
    temp_id VARCHAR(64) NOT NULL,
    description TEXT NULL,
    status VARCHAR(32) NULL,
    responsible_engineer_id INT NULL,
    notes TEXT NULL,
    created_by_user_id INT NOT NULL,
    last_modified_by_user_id INT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    modified_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    version INT DEFAULT 1,
    is_deleted BOOLEAN DEFAULT FALSE,
    FOREIGN KEY (shift_id) REFERENCES shift(id) ON DELETE CASCADE,
    FOREIGN KEY (created_by_user_id) REFERENCES user(id),
    FOREIGN KEY (last_modified_by_user_id) REFERENCES user(id),
    FOREIGN KEY (responsible_engineer_id) REFERENCES team_member(id),
    INDEX ix_draft_key_point_shift_id (shift_id),
    INDEX ix_draft_key_point_temp_id (temp_id),
    INDEX idx_draft_keypoints (shift_id, is_deleted)
);

-- Verify tables created
SELECT 'Collaboration tables created successfully!' AS status;
