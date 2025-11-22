-- Update user with all required fields
UPDATE user 
SET 
    password = 'scrypt:32768:8:1\\',
    is_active = 1,
    status = 'active'
WHERE username = 'superadmin';

-- Verify the user
SELECT id, username, email, role, is_active, status FROM user WHERE username = 'superadmin';
