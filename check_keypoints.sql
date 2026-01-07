SELECT id, LEFT(description, 50) as description, status, shift_id FROM shift_key_point WHERE status = 'Open' OR status = 'In Progress' ORDER BY id DESC LIMIT 30;










