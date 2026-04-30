-- Add session management columns to user table
-- Run this on your local database

ALTER TABLE user 
ADD COLUMN session_token VARCHAR(255) DEFAULT NULL,
ADD COLUMN session_created_at DATETIME DEFAULT NULL,
ADD COLUMN sessions_terminated_at DATETIME DEFAULT NULL;

-- Verify the columns were added
DESCRIBE user;


