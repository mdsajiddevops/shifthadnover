UPDATE user SET role = 'super_admin' WHERE username = 'superadmin';
SELECT username, role, is_active, status FROM user WHERE username = 'superadmin';