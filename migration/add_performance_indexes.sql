-- Performance optimization indexes for Archon
-- Run this in Supabase SQL Editor to add indexes for frequently queried columns
--
-- Impact: 10-100x faster queries for common operations

-- Index for sorting knowledge sources by updated_at (used in knowledge base list)
CREATE INDEX IF NOT EXISTS idx_sources_updated_at
ON archon_sources(updated_at DESC);

-- Index for filtering tasks by status (used in task lists and counts)
CREATE INDEX IF NOT EXISTS idx_tasks_status
ON archon_tasks(status);

-- Composite index for efficient task queries by project, status, and order
-- This supports: WHERE project_id = X AND status = Y ORDER BY task_order
CREATE INDEX IF NOT EXISTS idx_tasks_project_status_order
ON archon_tasks(project_id, status, task_order);

-- Index for document version queries by project
CREATE INDEX IF NOT EXISTS idx_document_versions_project
ON archon_document_versions(project_id);

-- Index for filtering sources by knowledge_type (used in filters)
CREATE INDEX IF NOT EXISTS idx_sources_knowledge_type
ON archon_sources(knowledge_type);

-- Index for searching sources by name (supports LIKE queries)
CREATE INDEX IF NOT EXISTS idx_sources_name_trgm
ON archon_sources USING gin(name gin_trgm_ops);

-- Index for code examples by source_id (used when displaying source details)
CREATE INDEX IF NOT EXISTS idx_code_examples_source
ON archon_code_examples(source_id);

-- Index for documents by source_id (used for chunk counts and queries)
CREATE INDEX IF NOT EXISTS idx_documents_source
ON archon_documents(source_id);

-- Verify indexes were created
SELECT
    schemaname,
    tablename,
    indexname,
    indexdef
FROM pg_indexes
WHERE schemaname = 'public'
    AND indexname LIKE 'idx_%'
ORDER BY tablename, indexname;
