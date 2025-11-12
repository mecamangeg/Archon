"""
Recent Changes Service for Archon
Phase 5, Task 5.4

Service for querying recent file changes in projects.
"""

from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta

from src.server.config.logfire_config import get_logger
from src.server.services.knowledge.codebase_source_service import CodebaseSourceService

logger = get_logger(__name__)


class RecentChangesService:
    """Service for querying recent file changes"""

    def __init__(self, db):
        """
        Initialize RecentChangesService

        Args:
            db: Supabase client instance
        """
        self.db = db
        self.codebase_service = CodebaseSourceService(db)

    async def get_recent_changes(
        self,
        project_id: str,
        days: int = 7,
        file_filter: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get files that changed recently in a project

        Args:
            project_id: UUID of the project
            days: Number of days to look back
            file_filter: Optional file pattern filter

        Returns:
            List of recently changed files with metadata

        Raises:
            ValueError: If project has no codebase source
        """
        try:
            # Get project's codebase source
            source = await self.codebase_service.get_by_project_id(project_id)

            if not source:
                raise ValueError(f"Project {project_id} has no synced codebase")

            cutoff_date = datetime.now() - timedelta(days=days)

            # Build query
            query = (
                self.db.table("knowledge_chunks")
                .select("file_path, language, updated_at, chunk_index")
                .eq("source_id", source["id"])
                .gte("updated_at", cutoff_date.isoformat())
            )

            # Apply file filter if provided
            if file_filter:
                sql_pattern = file_filter.replace("*", "%").replace("?", "_")
                query = query.like("file_path", sql_pattern)

            response = await query.order("updated_at", desc=True).execute()

            # Group by file path
            files_dict = {}
            for chunk in response.data:
                file_path = chunk["file_path"]
                if file_path not in files_dict:
                    files_dict[file_path] = {
                        "file_path": file_path,
                        "language": chunk.get("language"),
                        "last_updated": chunk["updated_at"],
                        "chunk_count": 1,
                    }
                else:
                    files_dict[file_path]["chunk_count"] += 1
                    # Keep most recent update time
                    if chunk["updated_at"] > files_dict[file_path]["last_updated"]:
                        files_dict[file_path]["last_updated"] = chunk["updated_at"]

            results = list(files_dict.values())

            # Sort by last_updated descending
            results.sort(key=lambda x: x["last_updated"], reverse=True)

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
            logger.error(
                f"Error getting recent changes: {str(e)}",
                extra={"project_id": project_id, "days": days, "error": str(e)},
            )
            raise

    async def get_changes_by_date(
        self,
        project_id: str,
        start_date: datetime,
        end_date: datetime,
    ) -> List[Dict[str, Any]]:
        """
        Get files changed within a specific date range

        Args:
            project_id: UUID of the project
            start_date: Start of date range
            end_date: End of date range

        Returns:
            List of changed files within date range

        Raises:
            ValueError: If project has no codebase source
        """
        try:
            source = await self.codebase_service.get_by_project_id(project_id)

            if not source:
                raise ValueError(f"Project {project_id} has no synced codebase")

            # Query chunks within date range
            response = (
                await self.db.table("knowledge_chunks")
                .select("file_path, language, updated_at")
                .eq("source_id", source["id"])
                .gte("updated_at", start_date.isoformat())
                .lte("updated_at", end_date.isoformat())
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
                        "language": chunk.get("language"),
                        "last_updated": chunk["updated_at"],
                        "chunk_count": 1,
                    }
                else:
                    files_dict[file_path]["chunk_count"] += 1

            results = list(files_dict.values())

            logger.info(
                f"Retrieved changes by date range",
                extra={
                    "project_id": project_id,
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat(),
                    "files_count": len(results),
                },
            )

            return results

        except Exception as e:
            logger.error(f"Error getting changes by date: {str(e)}")
            raise

    async def get_change_statistics(
        self, project_id: str, days: int = 30
    ) -> Dict[str, Any]:
        """
        Get statistics about recent changes

        Args:
            project_id: UUID of the project
            days: Number of days to analyze

        Returns:
            Dict with statistics

        Raises:
            ValueError: If project has no codebase source
        """
        try:
            source = await self.codebase_service.get_by_project_id(project_id)

            if not source:
                raise ValueError(f"Project {project_id} has no synced codebase")

            cutoff_date = datetime.now() - timedelta(days=days)

            # Get all changes in period
            response = (
                await self.db.table("knowledge_chunks")
                .select("file_path, language, updated_at")
                .eq("source_id", source["id"])
                .gte("updated_at", cutoff_date.isoformat())
                .execute()
            )

            chunks = response.data

            # Calculate statistics
            unique_files = set(chunk["file_path"] for chunk in chunks)
            language_counts = {}
            for chunk in chunks:
                lang = chunk.get("language", "unknown")
                language_counts[lang] = language_counts.get(lang, 0) + 1

            # Group changes by date
            changes_by_date = {}
            for chunk in chunks:
                date = chunk["updated_at"][:10]  # Extract YYYY-MM-DD
                changes_by_date[date] = changes_by_date.get(date, 0) + 1

            stats = {
                "total_files_changed": len(unique_files),
                "total_chunks_updated": len(chunks),
                "language_breakdown": language_counts,
                "changes_by_date": changes_by_date,
                "period_days": days,
            }

            logger.info(
                f"Generated change statistics",
                extra={
                    "project_id": project_id,
                    "days": days,
                    "files_changed": len(unique_files),
                },
            )

            return stats

        except Exception as e:
            logger.error(f"Error getting change statistics: {str(e)}")
            raise
