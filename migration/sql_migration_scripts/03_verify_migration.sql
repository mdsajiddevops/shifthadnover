-- ============================================
-- VERIFICATION QUERIES
-- Run these to verify successful migration
-- ============================================

-- ============================================
-- 1. RECORD COUNT SUMMARY
-- ============================================

SELECT 
    'RECORD COUNTS' as category,
    '' as details
UNION ALL
SELECT '---', '---'
UNION ALL SELECT 'Accounts', (SELECT COUNT(*)::text FROM account)
UNION ALL SELECT 'Teams', (SELECT COUNT(*)::text FROM team)
UNION ALL SELECT 'Users', (SELECT COUNT(*)::text FROM "user")
UNION ALL SELECT 'Team Members', (SELECT COUNT(*)::text FROM team_member)
UNION ALL SELECT 'User-Team Links', (SELECT COUNT(*)::text FROM user_team_memberships)
UNION ALL SELECT '---', '---'
UNION ALL SELECT 'Shifts (Handovers)', (SELECT COUNT(*)::text FROM shift)
UNION ALL SELECT 'Incidents', (SELECT COUNT(*)::text FROM incident)
UNION ALL SELECT 'Key Points', (SELECT COUNT(*)::text FROM shift_key_point)
UNION ALL SELECT 'Key Point Updates', (SELECT COUNT(*)::text FROM shift_key_point_update)
UNION ALL SELECT 'Change Infos', (SELECT COUNT(*)::text FROM shift_change_info)
UNION ALL SELECT 'KB Updates', (SELECT COUNT(*)::text FROM shift_kb_update)
UNION ALL SELECT '---', '---'
UNION ALL SELECT 'Shift Rosters', (SELECT COUNT(*)::text FROM shift_roster);

-- ============================================
-- 2. DATE RANGE OF SHIFTS
-- ============================================

SELECT 
    MIN(date) as earliest_shift,
    MAX(date) as latest_shift,
    COUNT(*) as total_shifts,
    COUNT(DISTINCT date) as unique_dates
FROM shift;

-- ============================================
-- 3. SHIFTS BY STATUS
-- ============================================

SELECT 
    status,
    COUNT(*) as count
FROM shift
GROUP BY status
ORDER BY count DESC;

-- ============================================
-- 4. SHIFTS BY TEAM
-- ============================================

SELECT 
    t.name as team_name,
    COUNT(s.id) as shift_count
FROM team t
LEFT JOIN shift s ON t.id = s.team_id
GROUP BY t.id, t.name
ORDER BY shift_count DESC;

-- ============================================
-- 5. INCIDENTS BY TYPE
-- ============================================

SELECT 
    type,
    status,
    COUNT(*) as count
FROM incident
GROUP BY type, status
ORDER BY type, count DESC;

-- ============================================
-- 6. KEY POINTS BY STATUS
-- ============================================

SELECT 
    status,
    COUNT(*) as count
FROM shift_key_point
GROUP BY status
ORDER BY count DESC;

-- ============================================
-- 7. RECENT HANDOVER ACTIVITY
-- ============================================

SELECT 
    date,
    current_shift_type,
    next_shift_type,
    status,
    submitted_at
FROM shift
ORDER BY submitted_at DESC NULLS LAST
LIMIT 20;

-- ============================================
-- 8. USER ACTIVITY CHECK
-- ============================================

SELECT 
    u.username,
    u.email,
    u.role,
    COUNT(DISTINCT utm.team_id) as team_count,
    u.is_active
FROM "user" u
LEFT JOIN user_team_memberships utm ON u.id = utm.user_id
GROUP BY u.id, u.username, u.email, u.role, u.is_active
ORDER BY team_count DESC
LIMIT 20;

-- ============================================
-- 9. FOREIGN KEY INTEGRITY CHECK
-- ============================================

-- Check for orphaned shifts (no valid team)
SELECT COUNT(*) as orphaned_shifts
FROM shift s
WHERE NOT EXISTS (SELECT 1 FROM team t WHERE t.id = s.team_id);

-- Check for orphaned incidents (no valid shift)
SELECT COUNT(*) as orphaned_incidents
FROM incident i
WHERE shift_id IS NOT NULL 
AND NOT EXISTS (SELECT 1 FROM shift s WHERE s.id = i.shift_id);

-- Check for orphaned key points (no valid shift)
SELECT COUNT(*) as orphaned_key_points
FROM shift_key_point kp
WHERE shift_id IS NOT NULL
AND NOT EXISTS (SELECT 1 FROM shift s WHERE s.id = kp.shift_id);

-- ============================================
-- 10. DATA INTEGRITY SUMMARY
-- ============================================

SELECT 
    'Data Integrity Check' as check_type,
    CASE 
        WHEN (
            SELECT COUNT(*) FROM shift s 
            WHERE NOT EXISTS (SELECT 1 FROM team t WHERE t.id = s.team_id)
        ) = 0 THEN '✅ PASS'
        ELSE '❌ FAIL'
    END as shifts_have_valid_teams,
    CASE 
        WHEN (
            SELECT COUNT(*) FROM incident i 
            WHERE shift_id IS NOT NULL 
            AND NOT EXISTS (SELECT 1 FROM shift s WHERE s.id = i.shift_id)
        ) = 0 THEN '✅ PASS'
        ELSE '❌ FAIL'
    END as incidents_have_valid_shifts,
    CASE 
        WHEN (
            SELECT COUNT(*) FROM shift_key_point kp 
            WHERE shift_id IS NOT NULL
            AND NOT EXISTS (SELECT 1 FROM shift s WHERE s.id = kp.shift_id)
        ) = 0 THEN '✅ PASS'
        ELSE '❌ FAIL'
    END as keypoints_have_valid_shifts;

-- ============================================
-- END OF VERIFICATION QUERIES
-- ============================================







