-- =====================================================
-- Migration: Add Multiple Team Support for Users
-- Purpose: Allow users to belong to multiple teams
-- Date: 2025-11-26
-- =====================================================

-- Create user_team_memberships table for many-to-many relationship
CREATE TABLE `user_team_memberships` (
  `id` int NOT NULL AUTO_INCREMENT,
  `user_id` int NOT NULL,
  `team_id` int NOT NULL,
  `account_id` int NOT NULL,
  `is_primary` tinyint(1) NOT NULL DEFAULT '0' COMMENT 'Indicates if this is the user primary team',
  `role` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT 'member' COMMENT 'Role within this specific team',
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `added_by_id` int DEFAULT NULL COMMENT 'User who added this team membership',
  `is_active` tinyint(1) NOT NULL DEFAULT '1',
  PRIMARY KEY (`id`),
  UNIQUE KEY `unique_user_team_per_account` (`user_id`, `team_id`, `account_id`),
  KEY `user_id` (`user_id`),
  KEY `team_id` (`team_id`),
  KEY `account_id` (`account_id`),
  KEY `added_by_id` (`added_by_id`),
  KEY `idx_primary_team` (`user_id`, `is_primary`),
  CONSTRAINT `user_team_memberships_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `user` (`id`) ON DELETE CASCADE,
  CONSTRAINT `user_team_memberships_ibfk_2` FOREIGN KEY (`team_id`) REFERENCES `team` (`id`) ON DELETE CASCADE,
  CONSTRAINT `user_team_memberships_ibfk_3` FOREIGN KEY (`account_id`) REFERENCES `account` (`id`) ON DELETE CASCADE,
  CONSTRAINT `user_team_memberships_ibfk_4` FOREIGN KEY (`added_by_id`) REFERENCES `user` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Migrate existing user team relationships to the new table
INSERT INTO `user_team_memberships` (`user_id`, `team_id`, `account_id`, `is_primary`, `created_at`)
SELECT 
    u.id as user_id,
    u.team_id as team_id,
    u.account_id as account_id,
    1 as is_primary,  -- Mark existing assignments as primary
    COALESCE(u.created_at, NOW()) as created_at
FROM `user` u 
WHERE u.team_id IS NOT NULL 
  AND u.account_id IS NOT NULL;

-- Create index for performance on common queries
CREATE INDEX `idx_user_teams_active` ON `user_team_memberships` (`user_id`, `is_active`);
CREATE INDEX `idx_team_members_active` ON `user_team_memberships` (`team_id`, `is_active`);
CREATE INDEX `idx_account_members` ON `user_team_memberships` (`account_id`, `is_active`);

-- Add constraint to ensure only one primary team per user per account
-- Note: This is handled at application level for better flexibility

-- Optional: Add audit trigger for tracking changes
DELIMITER $$
CREATE TRIGGER `user_team_memberships_audit` 
AFTER UPDATE ON `user_team_memberships` 
FOR EACH ROW 
BEGIN
    IF OLD.is_active != NEW.is_active OR OLD.is_primary != NEW.is_primary THEN
        INSERT INTO audit_log (
            user_id, 
            username, 
            action, 
            details, 
            timestamp
        ) VALUES (
            NEW.user_id,
            (SELECT username FROM user WHERE id = NEW.user_id),
            'User Team Membership Modified',
            CONCAT('Team ID: ', NEW.team_id, ', Primary: ', NEW.is_primary, ', Active: ', NEW.is_active),
            NOW()
        );
    END IF;
END$$
DELIMITER ;

-- Create a view for easy querying of user teams
CREATE VIEW `user_teams_view` AS
SELECT 
    u.id as user_id,
    u.username,
    u.email,
    u.first_name,
    u.last_name,
    utm.team_id,
    t.name as team_name,
    utm.account_id,
    a.name as account_name,
    utm.is_primary,
    utm.role as team_role,
    utm.is_active as membership_active,
    utm.created_at as membership_created
FROM user u
JOIN user_team_memberships utm ON u.id = utm.user_id
JOIN team t ON utm.team_id = t.id
JOIN account a ON utm.account_id = a.id
WHERE utm.is_active = 1 AND u.is_active = 1 AND t.is_active = 1;

-- Add comments to tables for documentation
ALTER TABLE `user_team_memberships` COMMENT = 'Many-to-many relationship table for users and teams with primary team designation';

-- Show statistics after migration
SELECT 'Migration Results:' as Info;
SELECT 
    COUNT(*) as total_memberships_created,
    COUNT(CASE WHEN is_primary = 1 THEN 1 END) as primary_memberships,
    COUNT(DISTINCT user_id) as users_with_teams,
    COUNT(DISTINCT team_id) as teams_with_members
FROM user_team_memberships;

-- Verify data integrity
SELECT 'Data Integrity Check:' as Info;
SELECT 
    user_id,
    COUNT(*) as primary_team_count
FROM user_team_memberships 
WHERE is_primary = 1 
GROUP BY user_id 
HAVING COUNT(*) > 1;  -- Should return empty result

-- Show sample data
SELECT 'Sample Data:' as Info;
SELECT * FROM user_teams_view LIMIT 5;