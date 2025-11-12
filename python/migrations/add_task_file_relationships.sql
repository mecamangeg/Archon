-- Migration: Task-File Relationship Tracking
-- Phase 5, Task 5.1
-- Created: 2025-11-12
-- Description: Add table to track relationships between tasks and project files

-- Create task_file_relationships table
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

-- Create indexes for efficient queries
CREATE INDEX IF NOT EXISTS idx_task_file_task_id ON task_file_relationships(task_id);
CREATE INDEX IF NOT EXISTS idx_task_file_project_id ON task_file_relationships(project_id);
CREATE INDEX IF NOT EXISTS idx_task_file_file_path ON task_file_relationships(file_path);

-- Add comment to table
COMMENT ON TABLE task_file_relationships IS 'Tracks relationships between tasks and project files for context-aware development';

-- Add column comments
COMMENT ON COLUMN task_file_relationships.relationship_type IS 'Type of relationship: implements, tests, documents, references';
COMMENT ON COLUMN task_file_relationships.confidence IS 'Confidence score for auto-detected relationships (0.0-1.0)';
COMMENT ON COLUMN task_file_relationships.created_by IS 'Source of relationship: user, auto, git-hook';
