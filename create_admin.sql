INSERT INTO user (username, email, password_hash, role, first_name, last_name, is_active, created_at) 
VALUES (
    'superadmin', 
    'admin@shifthandover.com', 
    'scrypt:32768:8:1\\',
    'admin',
    'Super',
    'Admin',
    1,
    NOW()
);
