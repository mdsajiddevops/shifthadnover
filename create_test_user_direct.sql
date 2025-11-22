-- Create test user for onboarding workflow testing

-- First, delete if exists
DELETE FROM user WHERE username = 'testuser';

-- Insert the test user with proper password hash
INSERT INTO user (
    username, 
    email, 
    password, 
    first_name, 
    last_name, 
    role, 
    is_active,
    needs_onboarding,
    default_account_id,
    default_team_id
) VALUES (
    'testuser',
    'testuser@epam.com',
    'scrypt:32768:8:1\\',
    'Test',
    'User',
    'user',
    1,
    1,
    NULL,
    NULL
);

-- Verify the user was created
SELECT 'TEST USER CREATED FOR ONBOARDING:' as status;
SELECT id, username, email, first_name, last_name, role, is_active, needs_onboarding 
FROM user 
WHERE username = 'testuser';
