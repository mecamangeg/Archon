-- Migration: Add sync_checkpoints table
-- Purpose: Enable checkpoint-based sync recovery
-- Date: 2025-11-12

BEGIN;

-- Create sync_checkpoints table
CREATE TABLE IF NOT EXISTS sync_checkpoints (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES archon_projects(id) ON DELETE CASCADE,
    sync_job_id UUID NOT NULL,
    checkpoint_data JSONB NOT NULL DEFAULT '{}',
    status TEXT NOT NULL CHECK (status IN ('active', 'completed', 'failed', 'rolled_back')) DEFAULT 'active',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for efficient queries
CREATE INDEX IF NOT EXISTS idx_sync_checkpoints_project_id
    ON sync_checkpoints(project_id);

CREATE INDEX IF NOT EXISTS idx_sync_checkpoints_sync_job_id
    ON sync_checkpoints(sync_job_id);

CREATE INDEX IF NOT EXISTS idx_sync_checkpoints_status
    ON sync_checkpoints(status);

CREATE INDEX IF NOT EXISTS idx_sync_checkpoints_created_at
    ON sync_checkpoints(created_at DESC);

-- Composite index for common queries
CREATE INDEX IF NOT EXISTS idx_sync_checkpoints_project_status
    ON sync_checkpoints(project_id, status, created_at DESC);

-- Add comments for documentation
COMMENT ON TABLE sync_checkpoints IS 'Sync operation checkpoints for recovery and rollback';
COMMENT ON COLUMN sync_checkpoints.sync_job_id IS 'Unique identifier for the sync job';
COMMENT ON COLUMN sync_checkpoints.checkpoint_data IS 'JSON object with files_processed, files_remaining, chunks_created, timestamp';
COMMENT ON COLUMN sync_checkpoints.status IS 'Checkpoint status: active (in progress), completed (finished), failed (errored), rolled_back (reverted)';

-- Create function for finding duplicate chunks
CREATE OR REPLACE FUNCTION find_duplicate_chunks(src_id TEXT)
RETURNS TABLE(chunk_hash TEXT, count BIGINT) AS $$
BEGIN
    RETURN QUERY
    SELECT
        metadata->>'chunk_hash' as chunk_hash,
        COUNT(*) as count
    FROM knowledge_chunks
    WHERE source_id = src_id
    AND metadata->>'chunk_hash' IS NOT NULL
    GROUP BY metadata->>'chunk_hash'
    HAVING COUNT(*) > 1;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION find_duplicate_chunks IS 'Find duplicate chunks by chunk_hash for integrity verification';

COMMIT;
