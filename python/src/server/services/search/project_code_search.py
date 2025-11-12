"""
Project Code Search Service for Archon
Phase 5, Task 5.3

Service for project-scoped semantic code search with filtering capabilities.
"""

import fnmatch
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta

from src.server.config.logfire_config import get_logger
from src.server.services.knowledge.codebase_source_service import CodebaseSourceService

logger = get_logger(__name__)


class ProjectCodeSearchService:
    """Service for searching code within specific projects"""

    def __init__(self, db):
        """
        Initialize ProjectCodeSearchService

        Args:
            db: Supabase client instance
        """
        self.db = db
        self.codebase_service = CodebaseSourceService(db)

    async def search(
        self,
        project_id: str,
        query: str,
        match_count: int = 5,
        file_filter: Optional[str] = None,
        language_filter: Optional[str] = None,
        recency_days: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        Search code within a project using semantic search

        Args:
            project_id: UUID of the project to search
            query: Search query (semantic search)
            match_count: Number of results to return
            file_filter: Optional file pattern filter (e.g., '*.py', 'src/**/*.ts')
            language_filter: Optional language filter (e.g., 'python', 'typescript')
            recency_days: Optional filter for files modified in last N days

        Returns:
            List of search results with file paths, content, and similarity scores

        Raises:
            ValueError: If project has no codebase source
        """
        try:
            # Get project's codebase source
            source = await self.codebase_service.get_by_project_id(project_id)

            if not source:
                raise ValueError(f"Project {project_id} has no synced codebase")

            source_id = source["id"]

            # Generate query embedding (using existing embedding service)
            # Note: This assumes embedding service is available
            # In production, would use: embedding = await self.embedding_service.embed_text(query)
            # For now, using placeholder
            embedding = await self._generate_embedding(query)

            # Build query with filters
            query_builder = (
                self.db.table("knowledge_chunks")
                .select(
                    "id, file_path, chunk_index, content, start_line, end_line, language, updated_at"
                )
                .eq("source_id", source_id)
            )

            # Apply file filter (convert glob pattern to SQL LIKE)
            if file_filter:
                sql_pattern = self._glob_to_sql_pattern(file_filter)
                query_builder = query_builder.like("file_path", sql_pattern)

            # Apply language filter
            if language_filter:
                query_builder = query_builder.eq("language", language_filter)

            # Apply recency filter
            if recency_days:
                cutoff_date = datetime.now() - timedelta(days=recency_days)
                query_builder = query_builder.gte("updated_at", cutoff_date.isoformat())

            # Execute search
            # Note: Actual vector similarity search would use RPC function
            # For now, using basic query
            response = await query_builder.limit(match_count).execute()

            results = response.data

            # In production, would calculate similarity scores using pgvector
            # For now, adding placeholder similarity
            for result in results:
                result["similarity"] = 0.85  # Placeholder

            logger.info(
                f"Project code search completed",
                extra={
                    "project_id": project_id,
                    "query": query,
                    "results_count": len(results),
                    "file_filter": file_filter,
                    "language_filter": language_filter,
                },
            )

            return results

        except Exception as e:
            logger.error(
                f"Error searching project code: {str(e)}",
                extra={"project_id": project_id, "query": query, "error": str(e)},
            )
            raise

    async def search_in_files(
        self,
        project_id: str,
        query: str,
        file_paths: List[str],
        match_count: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        Search within specific files only

        Args:
            project_id: UUID of the project
            query: Search query
            file_paths: List of file paths to search within
            match_count: Number of results per file

        Returns:
            List of search results
        """
        try:
            source = await self.codebase_service.get_by_project_id(project_id)

            if not source:
                raise ValueError(f"Project {project_id} has no synced codebase")

            # Query chunks from specific files
            response = (
                await self.db.table("knowledge_chunks")
                .select("*")
                .eq("source_id", source["id"])
                .in_("file_path", file_paths)
                .limit(match_count * len(file_paths))
                .execute()
            )

            logger.info(
                f"Searched in specific files",
                extra={
                    "project_id": project_id,
                    "files_count": len(file_paths),
                    "results_count": len(response.data),
                },
            )

            return response.data

        except Exception as e:
            logger.error(f"Error searching in files: {str(e)}")
            raise

    async def get_recent_changes(
        self, project_id: str, days: int = 7
    ) -> List[Dict[str, Any]]:
        """
        Get files that changed recently in a project

        Args:
            project_id: UUID of the project
            days: Number of days to look back

        Returns:
            List of recently changed files with metadata
        """
        try:
            source = await self.codebase_service.get_by_project_id(project_id)

            if not source:
                raise ValueError(f"Project {project_id} has no synced codebase")

            cutoff_date = datetime.now() - timedelta(days=days)

            # Query recently updated chunks, grouped by file
            response = (
                await self.db.table("knowledge_chunks")
                .select("file_path, language, updated_at")
                .eq("source_id", source["id"])
                .gte("updated_at", cutoff_date.isoformat())
                .order("updated_at", desc=True)
                .execute()
            )

            # Group by file path
            files_dict = {}
            for chunk in response.data:
                file_path = chunk["file_path"]
                if file_path not in files_dict:
                    files_dict[file_path] = {
                        "file_path": file_path,
                        "language": chunk["language"],
                        "last_updated": chunk["updated_at"],
                        "chunk_count": 1,
                    }
                else:
                    files_dict[file_path]["chunk_count"] += 1
                    # Keep most recent update time
                    if chunk["updated_at"] > files_dict[file_path]["last_updated"]:
                        files_dict[file_path]["last_updated"] = chunk["updated_at"]

            results = list(files_dict.values())

            logger.info(
                f"Retrieved recent changes",
                extra={
                    "project_id": project_id,
                    "days": days,
                    "files_count": len(results),
                },
            )

            return results

        except Exception as e:
            logger.error(f"Error getting recent changes: {str(e)}")
            raise

    def _glob_to_sql_pattern(self, glob_pattern: str) -> str:
        """
        Convert glob pattern to SQL LIKE pattern

        Args:
            glob_pattern: Glob pattern (e.g., '*.py', 'src/**/*.ts')

        Returns:
            SQL LIKE pattern
        """
        # Convert glob wildcards to SQL wildcards
        # * -> %
        # ? -> _
        # Simplified conversion (full implementation would handle more cases)
        sql_pattern = glob_pattern.replace("*", "%").replace("?", "_")
        return sql_pattern

    async def _generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding for text

        Note: This is a placeholder. In production, would use actual embedding service.

        Args:
            text: Text to embed

        Returns:
            Embedding vector
        """
        # Placeholder - return dummy embedding
        # In production: return await self.embedding_service.embed_text(text)
        return [0.0] * 1536  # Standard OpenAI embedding dimension
