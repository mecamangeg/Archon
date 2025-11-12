-- Migration: Add sync-related fields to projects table
-- File: migrations/add_project_sync_fields.sql
-- Phase: 1, Task: 1.1
-- Description: Adds columns for project codebase synchronization functionality

BEGIN;

-- Add local path column
ALTER TABLE projects
ADD COLUMN IF NOT EXISTS local_path TEXT;

-- Add sync mode column
ALTER TABLE projects
ADD COLUMN IF NOT EXISTS sync_mode TEXT DEFAULT 'manual';

-- Add constraint for valid sync modes
ALTER TABLE projects
ADD CONSTRAINT check_sync_mode
CHECK (sync_mode IN ('manual', 'realtime', 'periodic', 'git-hook'));

-- Add auto-sync toggle
ALTER TABLE projects
ADD COLUMN IF NOT EXISTS auto_sync_enabled BOOLEAN DEFAULT FALSE;

-- Add last sync timestamp
ALTER TABLE projects
ADD COLUMN IF NOT EXISTS last_sync_at TIMESTAMP;

-- Add sync status
ALTER TABLE projects
ADD COLUMN IF NOT EXISTS sync_status TEXT DEFAULT 'never_synced';

-- Add constraint for valid sync statuses
ALTER TABLE projects
ADD CONSTRAINT check_sync_status
CHECK (sync_status IN ('synced', 'syncing', 'error', 'never_synced'));

-- Add last error message for debugging
ALTER TABLE projects
ADD COLUMN IF NOT EXISTS last_sync_error TEXT;

-- Add codebase source ID reference (will link to knowledge_sources)
ALTER TABLE projects
ADD COLUMN IF NOT EXISTS codebase_source_id TEXT;

-- Create index for efficient querying
CREATE INDEX IF NOT EXISTS idx_projects_auto_sync
ON projects(auto_sync_enabled)
WHERE auto_sync_enabled = TRUE;

CREATE INDEX IF NOT EXISTS idx_projects_local_path
ON projects(local_path)
WHERE local_path IS NOT NULL;

COMMIT;

-- Rollback script (run if migration fails):
-- BEGIN;
-- DROP INDEX IF EXISTS idx_projects_auto_sync;
-- DROP INDEX IF EXISTS idx_projects_local_path;
-- ALTER TABLE projects DROP CONSTRAINT IF EXISTS check_sync_mode;
-- ALTER TABLE projects DROP CONSTRAINT IF EXISTS check_sync_status;
-- ALTER TABLE projects DROP COLUMN IF EXISTS local_path;
-- ALTER TABLE projects DROP COLUMN IF EXISTS sync_mode;
-- ALTER TABLE projects DROP COLUMN IF EXISTS auto_sync_enabled;
-- ALTER TABLE projects DROP COLUMN IF EXISTS last_sync_at;
-- ALTER TABLE projects DROP COLUMN IF EXISTS sync_status;
-- ALTER TABLE projects DROP COLUMN IF EXISTS last_sync_error;
-- ALTER TABLE projects DROP COLUMN IF EXISTS codebase_source_id;
-- COMMIT;
