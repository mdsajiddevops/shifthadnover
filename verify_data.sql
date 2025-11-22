SELECT COUNT(*) as total_accounts FROM account;
SELECT COUNT(*) as total_teams FROM team;
SELECT COUNT(*) as total_users FROM user;
SELECT role, COUNT(*) as count FROM user GROUP BY role;
SELECT a.name as account_name, COUNT(u.id) as user_count FROM account a LEFT JOIN user u ON a.id = u.account_id GROUP BY a.id, a.name;
