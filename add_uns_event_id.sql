-- SQL script to add UNS Event ID column to email_delivery_log table
-- Run this on production database before restarting the application

-- Add the uns_event_id column if it doesn't exist
ALTER TABLE email_delivery_log 
ADD COLUMN IF NOT EXISTS uns_event_id VARCHAR(100) NULL;

-- Add index for faster lookups
CREATE INDEX IF NOT EXISTS idx_uns_event_id ON email_delivery_log(uns_event_id);

-- Verify the column was added
DESCRIBE email_delivery_log;








