-- Add team-specific email configuration columns
-- Run this SQL script to add email_recipients and priority_alert_recipients to the team table

-- Add email_recipients column (if not exists)
SET @sql = 'ALTER TABLE team ADD COLUMN email_recipients TEXT NULL';
SET @column_exists = (
    SELECT COUNT(*) 
    FROM INFORMATION_SCHEMA.COLUMNS 
    WHERE table_schema = DATABASE() 
    AND table_name = 'team' 
    AND column_name = 'email_recipients'
);

SET @sql = IF(@column_exists = 0, @sql, 'SELECT "email_recipients column already exists" as message');
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- Add priority_alert_recipients column (if not exists)
SET @sql = 'ALTER TABLE team ADD COLUMN priority_alert_recipients TEXT NULL';
SET @column_exists = (
    SELECT COUNT(*) 
    FROM INFORMATION_SCHEMA.COLUMNS 
    WHERE table_schema = DATABASE() 
    AND table_name = 'team' 
    AND column_name = 'priority_alert_recipients'
);

SET @sql = IF(@column_exists = 0, @sql, 'SELECT "priority_alert_recipients column already exists" as message');
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- Verify the columns were added
SELECT 
    column_name, 
    data_type, 
    is_nullable 
FROM INFORMATION_SCHEMA.COLUMNS 
WHERE table_schema = DATABASE() 
    AND table_name = 'team' 
    AND column_name IN ('email_recipients', 'priority_alert_recipients')
ORDER BY column_name;