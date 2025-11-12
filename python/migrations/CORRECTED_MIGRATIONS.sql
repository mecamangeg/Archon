-- ========================================
-- CORRECTED MIGRATIONS - Run in Supabase SQL Editor
-- ========================================
-- Date: 2025-11-12
-- Purpose: Fix missing tables with corrected foreign key references
--
-- INSTRUCTIONS:
-- 1. Open Supabase Dashboard
-- 2. Go to SQL Editor
-- 3. Copy-paste this entire script
-- 4. Click "Run" to execute
-- ========================================

BEGIN;

-- ========================================
-- 1. Create sync_operations table
-- ========================================
-- FIXED: Changed projects(id) → archon_projects(id)
-- Purpose: Track all sync operations for analytics and monitoring

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

COMMENT ON TABLE sync_operations IS 'Tracks sync operations for analytics and monitoring';

-- ========================================
-- 2. Create task_file_relationships table
-- ========================================
-- FIXED: Changed tasks(id) → archon_tasks(id), projects(id) → archon_projects(id)
-- Purpose: Track relationships between tasks and project files

CREATE TABLE IF NOT EXISTS task_file_relationships (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id UUID NOT NULL REFERENCES archon_tasks(id) ON DELETE CASCADE,
    project_id UUID NOT NULL REFERENCES archon_projects(id) ON DELETE CASCADE,
    file_path TEXT NOT NULL,
    relationship_type TEXT NOT NULL CHECK (relationship_type IN ('implements', 'tests', 'documents', 'references')),
    confidence FLOAT DEFAULT 1.0 CHECK (confidence >= 0.0 AND confidence <= 1.0),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_by TEXT DEFAULT 'user' CHECK (created_by IN ('user', 'auto', 'git-hook')),
    UNIQUE(task_id, project_id, file_path)
);

-- Indexes for efficient queries
CREATE INDEX IF NOT EXISTS idx_task_file_task_id ON task_file_relationships(task_id);
CREATE INDEX IF NOT EXISTS idx_task_file_project_id ON task_file_relationships(project_id);
CREATE INDEX IF NOT EXISTS idx_task_file_file_path ON task_file_relationships(file_path);

-- Add comments
COMMENT ON TABLE task_file_relationships IS 'Tracks relationships between tasks and project files for context-aware development';
COMMENT ON COLUMN task_file_relationships.relationship_type IS 'Type of relationship: implements, tests, documents, references';
COMMENT ON COLUMN task_file_relationships.confidence IS 'Confidence score for auto-detected relationships (0.0-1.0)';
COMMENT ON COLUMN task_file_relationships.created_by IS 'Source of relationship: user, auto, git-hook';

COMMIT;

-- ========================================
-- VERIFICATION QUERIES
-- ========================================
-- Run these after the migration to verify success:

-- Check sync_operations exists
SELECT COUNT(*) as sync_operations_count FROM sync_operations;

-- Check task_file_relationships exists
SELECT COUNT(*) as task_file_count FROM task_file_relationships;

-- ========================================
-- ROLLBACK SCRIPT (if needed)
-- ========================================
-- Run this if you need to undo the migration:
/*
BEGIN;
DROP TABLE IF EXISTS sync_operations CASCADE;
DROP TABLE IF EXISTS task_file_relationships CASCADE;
COMMIT;
*/
