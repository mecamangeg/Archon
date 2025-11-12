# ⚠️ CRITICAL: Two-Table Embedding Architecture

## Before Running Migrations - Read This!

There are **TWO separate embedding tables** in the Archon ecosystem:

### 1. `cic_knowledge_embeddings` (CIC Learning System)
- **Owner**: archon-skill project
- **Purpose**: Error patterns, best practices, self-learning AI
- **Schema**: NO `metadata` column, uses `source_table` + `source_id`
- **Migration**: Run in archon-skill project

### 2. `knowledge_chunks` (Project Sync System)
- **Owner**: Main archon project
- **Purpose**: Project codebase embeddings for semantic search
- **Schema**: HAS `metadata` JSONB column with `file_path`
- **Migration**: `create_knowledge_chunks_table.sql` ✅ Created 2025-11-12

## Why This Matters

During sync integration (2025-11-12), this confusion caused 3+ hours of debugging:
- `knowledge_chunks` was designed but never created
- Sync service tried to use `cic_knowledge_embeddings` incorrectly
- Schema mismatches and type errors everywhere

## Before You Continue

✅ **Read full architecture doc**: `../DOCS/SCHEMA-ARCHITECTURE-TWO-TABLE-DESIGN.md`

✅ **Verify which table you need**:
- Working on CIC learning? → `cic_knowledge_embeddings`
- Working on project sync? → `knowledge_chunks`

✅ **Check table exists** before writing code:
```bash
# Check knowledge_chunks
python -c "from supabase import create_client; ..."
```

## Key Differences

| Feature | `cic_knowledge_embeddings` | `knowledge_chunks` |
|---------|---------------------------|-------------------|
| `metadata` column | ❌ None | ✅ JSONB |
| `source_id` type | UUID | TEXT |
| File path tracking | ❌ No | ✅ Yes |

**Don't assume they're interchangeable!**

---

**For full details**: See `../DOCS/SCHEMA-ARCHITECTURE-TWO-TABLE-DESIGN.md`
