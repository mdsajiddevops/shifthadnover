-- Local Testing Database Initialization
-- This file initializes some basic configuration for local testing

USE shift_handover;

-- Insert basic SMTP configuration if not exists
INSERT IGNORE INTO app_config (key_name, key_value, description, is_encrypted, created_at, updated_at) VALUES
('smtp_server', 'smtp.gmail.com', 'SMTP server for email sending', 0, NOW(), NOW()),
('smtp_port', '587', 'SMTP port', 0, NOW(), NOW()),
('team_email', 'mdsajid020@gmail.com', 'Default team email for notifications', 0, NOW(), NOW());

-- Insert admin user if not exists
INSERT IGNORE INTO user (username, email, full_name, role, is_admin, is_active, created_at) VALUES
('admin', 'admin@localhost', 'Local Admin', 'Admin', 1, 1, NOW());

-- Insert default password for admin user (password: admin123)
INSERT IGNORE INTO password_reset (username, email, reset_token, new_password_hash, created_at, expires_at, is_used) VALUES
('admin', 'admin@localhost', 'local_admin_setup', '$2b$12$LQv3c1yqBwarf16ABMO3TuYo4KGc9Dxl3Z0/h5Mq4B.vw8Qf1/gQS', NOW(), DATE_ADD(NOW(), INTERVAL 1 YEAR), 0);

-- Create default application config entries for email recipients
INSERT IGNORE INTO app_config (key_name, key_value, description, is_encrypted, created_at, updated_at) VALUES
('email_recipients', '["mdsajid020@gmail.com"]', 'List of email recipients for notifications', 0, NOW(), NOW()),
('email_enabled', 'true', 'Enable/disable email notifications', 0, NOW(), NOW());

COMMIT;