-- Clean up test data from shift_key_point (Pending Action Items)

-- Show current test key points
SELECT 'CURRENT TEST KEY POINTS:' as info;
SELECT id, description, status, responsible_engineer_id, shift_id 
FROM shift_key_point 
WHERE description LIKE '%test%' 
   OR description LIKE '%Test%' 
   OR description LIKE '%TEST%'
   OR description LIKE '%Testing%'
   OR description LIKE '%Key point%'
ORDER BY id DESC;

-- Show ALL key points to see what we have
SELECT 'ALL CURRENT KEY POINTS:' as info;
SELECT id, description, status, responsible_engineer_id, shift_id 
FROM shift_key_point 
ORDER BY id DESC;

-- Delete test key points
DELETE FROM shift_key_point 
WHERE description LIKE '%test%' 
   OR description LIKE '%Test%' 
   OR description LIKE '%TEST%'
   OR description LIKE '%Testing%'
   OR description LIKE '%Key point%';

-- Show remaining key points after cleanup
SELECT 'REMAINING KEY POINTS AFTER CLEANUP:' as info;
SELECT id, description, status, responsible_engineer_id, shift_id 
FROM shift_key_point 
ORDER BY id DESC;

-- Final count
SELECT 'FINAL KEY POINTS COUNT:' as info;
SELECT COUNT(*) as total_key_points FROM shift_key_point;
