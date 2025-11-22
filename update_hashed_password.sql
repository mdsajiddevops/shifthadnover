UPDATE user 
SET password = 'scrypt:32768:8:1\\' 
WHERE username = 'superadmin';
