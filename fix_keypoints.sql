-- Fix: Update all duplicate key points to Closed if there's a newer Closed version with same description
-- This is a one-time cleanup script

-- First, let's see how many will be affected
SELECT COUNT(*) as will_be_closed FROM shift_key_point kp1
WHERE kp1.status IN ('Open', 'In Progress')
AND EXISTS (
    SELECT 1 FROM (SELECT * FROM shift_key_point) kp2
    WHERE kp2.description = kp1.description
    AND kp2.account_id = kp1.account_id
    AND kp2.team_id = kp1.team_id
    AND kp2.status = 'Closed'
    AND kp2.id > kp1.id
);

-- Now update them using a subquery workaround for MySQL
UPDATE shift_key_point
SET status = 'Closed'
WHERE id IN (
    SELECT id FROM (
        SELECT kp1.id
        FROM shift_key_point kp1
        WHERE kp1.status IN ('Open', 'In Progress')
        AND EXISTS (
            SELECT 1 FROM (SELECT * FROM shift_key_point) kp2
            WHERE kp2.description = kp1.description
            AND kp2.account_id = kp1.account_id
            AND kp2.team_id = kp1.team_id
            AND kp2.status = 'Closed'
            AND kp2.id > kp1.id
        )
    ) as ids_to_update
);

-- Verify the fix
SELECT COUNT(*) as remaining_open FROM shift_key_point WHERE status IN ('Open', 'In Progress');
