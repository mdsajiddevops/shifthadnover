-- Database Migration Script
-- From old application version to new version with secrets management
-- Date: October 26, 2025
-- Target: GCP VM MySQL Database

USE shift_handover;

-- ===================================================
-- STEP 1: CREATE NEW TABLES FOR SECRETS MANAGEMENT
-- ===================================================

-- Create secret_store table for encrypted secrets management
CREATE TABLE IF NOT EXISTS secret_store (
    id INT AUTO_INCREMENT PRIMARY KEY,
    key_name VARCHAR(255) NOT NULL UNIQUE,
    encrypted_value TEXT NOT NULL,
    category VARCHAR(50) NOT NULL DEFAULT 'application',
    description TEXT,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    requires_restart BOOLEAN NOT NULL DEFAULT FALSE,
    
    -- Audit fields
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    created_by VARCHAR(255),
    updated_by VARCHAR(255),
    
    -- Security fields
    last_accessed DATETIME,
    access_count INT DEFAULT 0,
    expires_at DATETIME,
    
    INDEX idx_key_name (key_name),
    INDEX idx_category (category),
    INDEX idx_is_active (is_active)
);

-- ===================================================
-- STEP 2: VERIFY AND UPDATE EXISTING TABLE SCHEMAS
-- ===================================================

-- Check if app_config needs column name updates
-- Current VM has: config_key, config_value, description, category, created_at, updated_at
-- This should be compatible with new application, no changes needed

-- ===================================================
-- STEP 3: INSERT DEFAULT CONFIGURATION VALUES
-- ===================================================

-- Insert default email configuration if not exists
INSERT IGNORE INTO app_config (config_key, config_value, description, category, created_at, updated_at) VALUES
('email_recipients', '["mdsajid020@gmail.com"]', 'List of email recipients for shift handover notifications', 'email', NOW(), NOW()),
('email_enabled', 'true', 'Enable/disable email notifications', 'email', NOW(), NOW()),
('smtp_encryption_enabled', 'false', 'Use encrypted SMTP credentials', 'email', NOW(), NOW());

-- Insert feature toggle configurations
INSERT IGNORE INTO app_config (config_key, config_value, description, category, created_at, updated_at) VALUES
('tab_kb_articles', 'false', 'Enable/Disable KB Articles tab', 'tabs', NOW(), NOW()),
('tab_vendor_details', 'false', 'Enable/Disable Vendor Details tab', 'tabs', NOW(), NOW()),
('tab_application_details', 'false', 'Enable/Disable Application Details tab', 'tabs', NOW(), NOW()),
('servicenow_integration_enabled', 'false', 'Enable ServiceNow integration', 'integrations', NOW(), NOW()),
('secrets_management_enabled', 'true', 'Enable secrets management interface', 'security', NOW(), NOW());

-- Insert shift timing configurations
INSERT IGNORE INTO app_config (config_key, config_value, description, category, created_at, updated_at) VALUES
('app_timezone', 'Asia/Kolkata', 'Application timezone', 'general', NOW(), NOW()),
('morning_shift_start', '09:00', 'Morning shift start time', 'shifts', NOW(), NOW()),
('morning_shift_end', '18:00', 'Morning shift end time', 'shifts', NOW(), NOW()),
('evening_shift_start', '18:00', 'Evening shift start time', 'shifts', NOW(), NOW()),
('evening_shift_end', '02:00', 'Evening shift end time', 'shifts', NOW(), NOW()),
('night_shift_start', '02:00', 'Night shift start time', 'shifts', NOW(), NOW()),
('night_shift_end', '09:00', 'Night shift end time', 'shifts', NOW(), NOW());

-- ===================================================
-- STEP 4: INITIALIZE ENCRYPTED SECRETS (OPTIONAL)
-- ===================================================

-- Note: These will be populated through the admin interface
-- after deployment, but we can add placeholders

INSERT IGNORE INTO secret_store (key_name, encrypted_value, category, description, created_by) VALUES
('smtp_username', 'placeholder_encrypted_value', 'external', 'SMTP username for email notifications', 'migration_script'),
('smtp_password', 'placeholder_encrypted_value', 'external', 'SMTP password for email notifications', 'migration_script'),
('servicenow_username', 'placeholder_encrypted_value', 'external', 'ServiceNow integration username', 'migration_script'),
('servicenow_password', 'placeholder_encrypted_value', 'external', 'ServiceNow integration password', 'migration_script'),
('servicenow_instance_url', 'placeholder_encrypted_value', 'external', 'ServiceNow instance URL', 'migration_script');

-- ===================================================
-- STEP 5: UPDATE EXISTING DATA (IF NEEDED)
-- ===================================================

-- Update any existing configuration values that might need adjustment
UPDATE app_config SET 
    category = 'email' 
WHERE config_key IN ('smtp_server', 'smtp_port', 'team_email') 
AND category != 'email';

-- ===================================================
-- STEP 6: VERIFY MIGRATION
-- ===================================================

-- Show summary of changes
SELECT 'Tables created/verified' as status, COUNT(*) as count FROM information_schema.tables 
WHERE table_schema = 'shift_handover' AND table_name = 'secret_store';

SELECT 'App config entries' as status, COUNT(*) as count FROM app_config;

SELECT 'Secret store entries' as status, COUNT(*) as count FROM secret_store;

-- Show all configuration categories
SELECT category, COUNT(*) as config_count FROM app_config GROUP BY category ORDER BY category;

COMMIT;

-- ===================================================
-- MIGRATION COMPLETED
-- ===================================================
-- Next steps:
-- 1. Deploy new application code
-- 2. Configure secrets through admin interface
-- 3. Test email functionality
-- 4. Verify all features are working
-- ===================================================