-- Try different role values that might be expected
UPDATE user SET role = 'superadmin' WHERE username = 'superadmin';

-- Check if we have any reference data about expected roles
SELECT DISTINCT role FROM user;

-- Check what's in app_config
SELECT config_key, config_value FROM app_config LIMIT 10;
