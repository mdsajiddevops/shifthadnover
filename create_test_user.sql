-- Create test user for onboarding workflow testing
INSERT INTO user (
    username, 
    email, 
    password_hash, 
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
    'pbkdf2:sha256:600000\\',
    'Test',
    'User',
    'user',
    1,
    1,
    NULL,
    NULL
);

-- Verify the user was created
SELECT 'TEST USER CREATED:' as status;
SELECT id, username, email, first_name, last_name, role, is_active, needs_onboarding 
FROM user 
WHERE username = 'testuser';
