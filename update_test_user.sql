-- Update existing test user for onboarding workflow testing

UPDATE user 
SET 
    password = 'scrypt:32768:8:1\\',
    email = 'testuser@epam.com',
    role = 'user',
    first_login = 1,
    onboarding_completed = 0,
    account_id = NULL,
    team_id = NULL
WHERE username = 'testuser';

-- Verify the user was updated
SELECT 'TEST USER UPDATED FOR ONBOARDING:' as status;
SELECT id, username, email, first_name, last_name, role, is_active, first_login, onboarding_completed, account_id, team_id
FROM user 
WHERE username = 'testuser';
