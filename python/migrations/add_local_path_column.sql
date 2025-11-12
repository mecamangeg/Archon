-- Migration: Add local_path column to archon_projects
-- Purpose: Store local filesystem path for sync operations
-- Date: 2025-11-12

BEGIN;

-- Add local_path column
ALTER TABLE archon_projects
ADD COLUMN IF NOT EXISTS local_path TEXT;

-- Add index for efficient querying
CREATE INDEX IF NOT EXISTS idx_archon_projects_local_path
    ON archon_projects(local_path)
    WHERE local_path IS NOT NULL;

-- Add comment for documentation
COMMENT ON COLUMN archon_projects.local_path IS 'Absolute path to project directory on local filesystem for sync operations';

COMMIT;
