-- Migration: Create knowledge_chunks table for project codebase embeddings
-- Purpose: Store chunked codebase content with embeddings for semantic search
-- Date: 2025-11-12

BEGIN;

-- Create knowledge_chunks table for Archon project codebases
-- (Separate from cic_knowledge_embeddings which is for CIC learning system)
CREATE TABLE IF NOT EXISTS knowledge_chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_id TEXT NOT NULL REFERENCES archon_sources(source_id) ON DELETE CASCADE,
    chunk_text TEXT NOT NULL,
    chunk_index INTEGER NOT NULL,  -- Order within file
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    -- Metadata structure:
    -- {
    --   "file_path": "relative/path/to/file.ext",
    --   "file_type": "py",
    --   "language": "python",
    --   "start_line": 1,
    --   "end_line": 50,
    --   "chunk_size": 500
    -- }
    embedding vector(384),  -- Sentence transformers dimension (all-MiniLM-L6-v2)
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for efficient querying
CREATE INDEX IF NOT EXISTS idx_chunks_source_id ON knowledge_chunks(source_id);
CREATE INDEX IF NOT EXISTS idx_chunks_file_path ON knowledge_chunks((metadata->>'file_path'));
CREATE INDEX IF NOT EXISTS idx_chunks_source_file ON knowledge_chunks(source_id, (metadata->>'file_path'));
CREATE INDEX IF NOT EXISTS idx_chunks_created_at ON knowledge_chunks(created_at DESC);

-- Create ivfflat index for fast vector similarity search
CREATE INDEX IF NOT EXISTS idx_chunks_embedding_ivfflat
ON knowledge_chunks
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

-- Add trigger for updated_at timestamp
CREATE TRIGGER update_knowledge_chunks_updated_at
BEFORE UPDATE ON knowledge_chunks
FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Add table comment
COMMENT ON TABLE knowledge_chunks IS 'Chunked project codebase content with vector embeddings for semantic search (Archon project sync system)';

COMMIT;
