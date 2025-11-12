-- Migration: Add last_sync_error column to archon_projects
-- Purpose: Store last sync error message for debugging
-- Date: 2025-11-12

BEGIN;

-- Add last_sync_error column
ALTER TABLE archon_projects
ADD COLUMN IF NOT EXISTS last_sync_error TEXT;

-- Add comment for documentation
COMMENT ON COLUMN archon_projects.last_sync_error IS 'Last sync error message for debugging (cleared on successful sync)';

COMMIT;
