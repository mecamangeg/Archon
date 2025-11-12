-- Migration: Add count_unique_files database function
-- File: migrations/add_count_unique_files_function.sql
-- Purpose: Count unique files in a codebase source

CREATE OR REPLACE FUNCTION count_unique_files(src_id TEXT)
RETURNS INTEGER AS $$
BEGIN
    RETURN (
        SELECT COUNT(DISTINCT metadata->>'file_path')
        FROM knowledge_chunks
        WHERE source_id = src_id
    );
END;
$$ LANGUAGE plpgsql;
