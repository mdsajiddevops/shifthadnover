-- Migration script to create team_feature_config table
-- This table stores feature/tab visibility configuration for teams and accounts

CREATE TABLE IF NOT EXISTS `team_feature_config` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `scope_type` VARCHAR(20) NOT NULL COMMENT 'account or team',
    `scope_id` INT NOT NULL COMMENT 'account_id or team_id',
    `feature_key` VARCHAR(128) NOT NULL COMMENT 'Feature/tab identifier (e.g., tab_problem_tickets)',
    `is_enabled` BOOLEAN NOT NULL DEFAULT TRUE COMMENT 'Whether the feature is enabled for this scope',
    `description` TEXT NULL COMMENT 'Optional description',
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    `created_by` VARCHAR(255) NULL COMMENT 'Username of person who created this config',
    `updated_by` VARCHAR(255) NULL COMMENT 'Username of person who last updated this config',
    UNIQUE KEY `uq_scope_feature` (`scope_type`, `scope_id`, `feature_key`),
    INDEX `idx_scope_type_id` (`scope_type`, `scope_id`),
    INDEX `idx_feature_key` (`feature_key`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Feature visibility configuration per account/team';
