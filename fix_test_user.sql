-- Fix test user for onboarding workflow testing

UPDATE user 
SET 
    password = 'scrypt:32768:8:1\\',
    email = 'testuser@epam.com',
    role = 'user',
    first_login = 1,
    onboarding_completed = 0,
    account_id = NULL,
    team_id = NULL,
    status = 'active',
    is_active = 1
WHERE username = 'testuser';

-- Verify the user was updated correctly
SELECT 'TEST USER FIXED:' as status;
SELECT id, username, email, role, is_active, status, first_login, onboarding_completed, account_id, team_id
FROM user 
WHERE username = 'testuser';

-- Show first part of password hash to verify it changed
SELECT 'PASSWORD HASH UPDATED:' as info;
SELECT username, SUBSTRING(password, 1, 50) as password_start
FROM user 
WHERE username = 'testuser';
