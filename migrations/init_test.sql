-- Test Database Initialization Script
-- This creates basic test data for multi-team functionality testing

-- Create test accounts
INSERT IGNORE INTO account (id, name, description, is_active, created_at, updated_at) VALUES
(1, 'Test Corporation', 'Test company for multi-team testing', 1, NOW(), NOW()),
(2, 'Demo Industries', 'Demo company for testing', 1, NOW(), NOW());

-- Create test teams
INSERT IGNORE INTO team (id, name, account_id, description, status, is_active, created_at, updated_at) VALUES
(1, 'DevOps Team', 1, 'Development Operations Team', 'active', 1, NOW(), NOW()),
(2, 'Support Team', 1, 'Customer Support Team', 'active', 1, NOW(), NOW()),
(3, 'Infrastructure Team', 1, 'Infrastructure Management Team', 'active', 1, NOW(), NOW()),
(4, 'Demo Team A', 2, 'Demo Team Alpha', 'active', 1, NOW(), NOW()),
(5, 'Demo Team B', 2, 'Demo Team Beta', 'active', 1, NOW(), NOW());

-- Create test super admin user
INSERT IGNORE INTO user (id, username, email, password, first_name, last_name, role, account_id, is_active, status, onboarding_completed, first_login, created_at, updated_at) VALUES
(1, 'superadmin', 'admin@testcorp.com', 'scrypt:32768:8:1$RVJaQzZGQUlGakc4$0a7c8f3c79a8c2e4b1d5e6f7g8h9i0j1k2l3m4n5o6p7q8r9s0t1u2v3w4x5y6z7', 'Super', 'Admin', 'super_admin', 1, 1, 'active', 1, 1, NOW(), NOW());

-- Create test account admin user
INSERT IGNORE INTO user (id, username, email, password, first_name, last_name, role, account_id, is_active, status, onboarding_completed, first_login, created_at, updated_at) VALUES
(2, 'accountadmin', 'account@testcorp.com', 'scrypt:32768:8:1$RVJaQzZGQUlGakc4$0a7c8f3c79a8c2e4b1d5e6f7g8h9i0j1k2l3m4n5o6p7q8r9s0t1u2v3w4x5y6z7', 'Account', 'Admin', 'account_admin', 1, 1, 'active', 1, 1, NOW(), NOW());

-- Create test regular users
INSERT IGNORE INTO user (id, username, email, password, first_name, last_name, role, account_id, is_active, status, onboarding_completed, first_login, created_at, updated_at) VALUES
(3, 'alice', 'alice@testcorp.com', 'scrypt:32768:8:1$RVJaQzZGQUlGakc4$0a7c8f3c79a8c2e4b1d5e6f7g8h9i0j1k2l3m4n5o6p7q8r9s0t1u2v3w4x5y6z7', 'Alice', 'Johnson', 'user', 1, 1, 'active', 1, 1, NOW(), NOW()),
(4, 'bob', 'bob@testcorp.com', 'scrypt:32768:8:1$RVJaQzZGQUlGakc4$0a7c8f3c79a8c2e4b1d5e6f7g8h9i0j1k2l3m4n5o6p7q8r9s0t1u2v3w4x5y6z7', 'Bob', 'Smith', 'user', 1, 1, 'active', 1, 1, NOW(), NOW()),
(5, 'charlie', 'charlie@testcorp.com', 'scrypt:32768:8:1$RVJaQzZGQUlGakc4$0a7c8f3c79a8c2e4b1d5e6f7g8h9i0j1k2l3m4n5o6p7q8r9s0t1u2v3w4x5y6z7', 'Charlie', 'Brown', 'user', 1, 1, 'active', 1, 1, NOW(), NOW());

-- Create some team members
INSERT IGNORE INTO team_member (id, name, email, contact_number, role, team_id, account_id, user_id, is_active, created_at, updated_at) VALUES
(1, 'alice', 'alice@testcorp.com', '123-456-7890', 'Engineer', 1, 1, 3, 1, NOW(), NOW()),
(2, 'bob', 'bob@testcorp.com', '123-456-7891', 'Senior Engineer', 2, 1, 4, 1, NOW(), NOW()),
(3, 'charlie', 'charlie@testcorp.com', '123-456-7892', 'Lead Engineer', 3, 1, 5, 1, NOW(), NOW());

-- Note: After migration, these users will be converted to multi-team memberships
-- Alice will belong to DevOps Team (primary)
-- Bob will belong to Support Team (primary) 
-- Charlie will belong to Infrastructure Team (primary)
-- Super admin can then add them to additional teams for testing

-- Create some basic shift roster data for testing
INSERT IGNORE INTO shift_roster (date, shift_code, team_member_id, team_id, account_id, created_at) VALUES
(CURDATE(), 'D', 1, 1, 1, NOW()),
(CURDATE(), 'E', 2, 2, 1, NOW()),
(CURDATE(), 'N', 3, 3, 1, NOW()),
(DATE_ADD(CURDATE(), INTERVAL 1 DAY), 'D', 2, 2, 1, NOW()),
(DATE_ADD(CURDATE(), INTERVAL 1 DAY), 'E', 3, 3, 1, NOW()),
(DATE_ADD(CURDATE(), INTERVAL 1 DAY), 'N', 1, 1, 1, NOW());

-- Add some application configurations
INSERT IGNORE INTO app_config (config_key, config_value, description, created_at, updated_at) VALUES
('app_name', 'Shift Handover - Test Environment', 'Application name for testing', NOW(), NOW()),
('enable_multi_team', 'true', 'Enable multi-team functionality', NOW(), NOW()),
('test_mode', 'true', 'Application is in test mode', NOW(), NOW());

SELECT 'Test data initialization completed' as status;