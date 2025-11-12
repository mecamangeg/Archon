-- Migration: Add sync_error_log table
-- Purpose: Track sync errors for debugging and monitoring
-- Date: 2025-11-12

BEGIN;

-- Create sync_error_log table
CREATE TABLE IF NOT EXISTS sync_error_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID REFERENCES archon_projects(id) ON DELETE CASCADE,
    error_type TEXT NOT NULL CHECK (error_type IN (
        'network',
        'permission',
        'parsing',
        'embedding',
        'database',
        'circuit_breaker',
        'unknown'
    )),
    error_message TEXT NOT NULL,
    error_details JSONB DEFAULT '{}',
    file_path TEXT,
    retry_count INTEGER DEFAULT 0,
    resolved BOOLEAN DEFAULT FALSE,
    occurred_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for efficient queries
CREATE INDEX IF NOT EXISTS idx_sync_error_log_project_id
    ON sync_error_log(project_id);

CREATE INDEX IF NOT EXISTS idx_sync_error_log_error_type
    ON sync_error_log(error_type);

CREATE INDEX IF NOT EXISTS idx_sync_error_log_occurred_at
    ON sync_error_log(occurred_at DESC);

CREATE INDEX IF NOT EXISTS idx_sync_error_log_resolved
    ON sync_error_log(resolved)
    WHERE resolved = FALSE;

-- Composite index for common queries
CREATE INDEX IF NOT EXISTS idx_sync_error_log_project_unresolved
    ON sync_error_log(project_id, occurred_at DESC)
    WHERE resolved = FALSE;

-- Add comments for documentation
COMMENT ON TABLE sync_error_log IS 'Tracks sync operation errors for debugging and monitoring';
COMMENT ON COLUMN sync_error_log.error_type IS 'Category of error: network, permission, parsing, embedding, database, circuit_breaker, unknown';
COMMENT ON COLUMN sync_error_log.error_details IS 'JSON object with stack traces, context, and additional debugging information';
COMMENT ON COLUMN sync_error_log.retry_count IS 'Number of retry attempts made before failure';
COMMENT ON COLUMN sync_error_log.resolved IS 'Whether the error has been resolved or acknowledged';

COMMIT;
