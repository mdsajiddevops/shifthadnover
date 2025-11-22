INSERT INTO user (username, email, password, role, is_active, status) 
VALUES (
    'superadmin', 
    'admin@shifthandover.com', 
    'scrypt:32768:8:1\\',
    'admin',
    1,
    'active'
);
