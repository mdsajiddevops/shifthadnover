-- Migration: Add DraftChangeInfo and DraftKBUpdate tables for collaborative editing
-- Run this against the shift_handover database

USE shift_handover;

-- Create DraftChangeInfo table
CREATE TABLE IF NOT EXISTS draft_change_info (
    id INT AUTO_INCREMENT PRIMARY KEY,
    shift_id INT NOT NULL,
    temp_id VARCHAR(100) NOT NULL,
    application_name VARCHAR(200),
    change_number VARCHAR(100),
    description TEXT,
    responsible_engineer_id INT,
    status VARCHAR(50) DEFAULT 'New',
    version INT DEFAULT 1,
    created_by_id INT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    -- Foreign keys
    FOREIGN KEY (shift_id) REFERENCES shifts(id) ON DELETE CASCADE,
    FOREIGN KEY (responsible_engineer_id) REFERENCES team_members(id) ON DELETE SET NULL,
    FOREIGN KEY (created_by_id) REFERENCES users(id) ON DELETE CASCADE,
    
    -- Unique constraint to prevent duplicates
    UNIQUE KEY unique_draft_changeinfo (shift_id, temp_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Create DraftKBUpdate table
CREATE TABLE IF NOT EXISTS draft_kb_update (
    id INT AUTO_INCREMENT PRIMARY KEY,
    shift_id INT NOT NULL,
    temp_id VARCHAR(100) NOT NULL,
    application_name VARCHAR(200),
    kb_number VARCHAR(100),
    description TEXT,
    responsible_engineer_id INT,
    status VARCHAR(50) DEFAULT 'New',
    version INT DEFAULT 1,
    created_by_id INT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    -- Foreign keys
    FOREIGN KEY (shift_id) REFERENCES shifts(id) ON DELETE CASCADE,
    FOREIGN KEY (responsible_engineer_id) REFERENCES team_members(id) ON DELETE SET NULL,
    FOREIGN KEY (created_by_id) REFERENCES users(id) ON DELETE CASCADE,
    
    -- Unique constraint to prevent duplicates
    UNIQUE KEY unique_draft_kbupdate (shift_id, temp_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Add indexes for better query performance
CREATE INDEX idx_draft_changeinfo_shift ON draft_change_info(shift_id);
CREATE INDEX idx_draft_changeinfo_created_by ON draft_change_info(created_by_id);
CREATE INDEX idx_draft_kbupdate_shift ON draft_kb_update(shift_id);
CREATE INDEX idx_draft_kbupdate_created_by ON draft_kb_update(created_by_id);

-- Verify tables were created
SELECT 'DraftChangeInfo table created' AS status;
SELECT 'DraftKBUpdate table created' AS status;
