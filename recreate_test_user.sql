-- Completely recreate test user for onboarding workflow testing

-- Delete existing test user
DELETE FROM user WHERE username = 'testuser';

-- Insert new test user with fresh hash and correct settings
INSERT INTO user (
    username, 
    email, 
    password, 
    first_name, 
    last_name, 
    role, 
    is_active,
    status,
    first_login,
    onboarding_completed,
    account_id,
    team_id
) VALUES (
    'testuser',
    'testuser@epam.com',
    'scrypt:32768:8:1\\',
    'Test',
    'User',
    'user',
    1,
    'active',
    1,
    0,
    NULL,
    NULL
);

-- Verify the new user
SELECT 'NEW TEST USER CREATED:' as status;
SELECT id, username, email, role, is_active, status, first_login, onboarding_completed, account_id, team_id
FROM user 
WHERE username = 'testuser';
