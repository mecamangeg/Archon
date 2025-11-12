-- Add Sync Operations Table for Analytics
-- Phase 5, Task 5.6
-- Table to track all sync operations for analytics and monitoring

CREATE TABLE IF NOT EXISTS sync_operations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES archon_projects(id) ON DELETE CASCADE,
    trigger TEXT NOT NULL CHECK (trigger IN ('manual', 'auto', 'git-hook', 'realtime', 'periodic')),
    started_at TIMESTAMP WITH TIME ZONE NOT NULL,
    completed_at TIMESTAMP WITH TIME ZONE,
    status TEXT NOT NULL CHECK (status IN ('running', 'success', 'error')),
    files_processed INT DEFAULT 0,
    chunks_added INT DEFAULT 0,
    chunks_modified INT DEFAULT 0,
    chunks_deleted INT DEFAULT 0,
    duration_seconds FLOAT,
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for efficient queries
CREATE INDEX IF NOT EXISTS idx_sync_ops_project_id ON sync_operations(project_id);
CREATE INDEX IF NOT EXISTS idx_sync_ops_started_at ON sync_operations(started_at);
CREATE INDEX IF NOT EXISTS idx_sync_ops_status ON sync_operations(status);
CREATE INDEX IF NOT EXISTS idx_sync_ops_trigger ON sync_operations(trigger);

-- Rollback
-- DROP TABLE IF EXISTS sync_operations;
