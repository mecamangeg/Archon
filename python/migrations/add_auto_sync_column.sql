-- Migration: Add auto_sync_enabled column to archon_projects
-- Purpose: Enable/disable automatic sync for projects
-- Date: 2025-11-12

BEGIN;

-- Add auto_sync_enabled column (defaults to false for safety)
ALTER TABLE archon_projects
ADD COLUMN IF NOT EXISTS auto_sync_enabled BOOLEAN DEFAULT FALSE;

-- Add index for filtering synced projects
CREATE INDEX IF NOT EXISTS idx_archon_projects_auto_sync_enabled
    ON archon_projects(auto_sync_enabled)
    WHERE auto_sync_enabled = TRUE;

-- Add last_sync_at column to track sync status
ALTER TABLE archon_projects
ADD COLUMN IF NOT EXISTS last_sync_at TIMESTAMP WITH TIME ZONE;

-- Add sync_status column to track sync health
ALTER TABLE archon_projects
ADD COLUMN IF NOT EXISTS sync_status TEXT CHECK (sync_status IN ('idle', 'syncing', 'completed', 'error')) DEFAULT 'idle';

-- Add index for sync status queries
CREATE INDEX IF NOT EXISTS idx_archon_projects_sync_status
    ON archon_projects(sync_status);

-- Add comments for documentation
COMMENT ON COLUMN archon_projects.auto_sync_enabled IS 'Whether automatic sync is enabled for this project';
COMMENT ON COLUMN archon_projects.last_sync_at IS 'Timestamp of the last successful sync operation';
COMMENT ON COLUMN archon_projects.sync_status IS 'Current sync status: idle (not running), syncing (in progress), completed (successful), error (failed)';

COMMIT;
