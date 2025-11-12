"""
Task File Service Module for Archon
Phase 5, Task 5.1

This module provides functionality to link tasks with project files,
enabling context-aware development and automatic relationship detection.
"""

import re
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from src.server.config.logfire_config import get_logger

logger = get_logger(__name__)


class TaskFileService:
    """Service for managing task-file relationships"""

    def __init__(self, db):
        """
        Initialize TaskFileService

        Args:
            db: Supabase client instance
        """
        self.db = db

    async def link_task_to_file(
        self,
        task_id: str,
        project_id: str,
        file_path: str,
        relationship_type: str = "implements",
        confidence: float = 1.0,
        created_by: str = "user",
    ) -> Dict[str, Any]:
        """
        Create a link between a task and a file

        Args:
            task_id: UUID of the task
            project_id: UUID of the project
            file_path: Path to file relative to project root
            relationship_type: Type of relationship (implements, tests, documents, references)
            confidence: Confidence score for auto-detected relationships (0.0-1.0)
            created_by: Source of relationship (user, auto, git-hook)

        Returns:
            Dict containing the created relationship

        Raises:
            ValueError: If parameters are invalid
        """
        try:
            # Validate inputs
            if relationship_type not in ["implements", "tests", "documents", "references"]:
                raise ValueError(f"Invalid relationship_type: {relationship_type}")

            if not 0.0 <= confidence <= 1.0:
                raise ValueError(f"Confidence must be between 0.0 and 1.0, got {confidence}")

            if created_by not in ["user", "auto", "git-hook"]:
                raise ValueError(f"Invalid created_by: {created_by}")

            # Create relationship
            data = {
                "task_id": task_id,
                "project_id": project_id,
                "file_path": file_path,
                "relationship_type": relationship_type,
                "confidence": confidence,
                "created_by": created_by,
            }

            response = await self.db.table("task_file_relationships").insert(data).execute()

            logger.info(
                f"Linked task {task_id} to file {file_path}",
                extra={
                    "task_id": task_id,
                    "file_path": file_path,
                    "relationship_type": relationship_type,
                },
            )

            return response.data[0] if response.data else {}

        except Exception as e:
            logger.error(
                f"Error linking task to file: {str(e)}",
                extra={"task_id": task_id, "file_path": file_path, "error": str(e)},
            )
            raise

    async def unlink_task_from_file(
        self, task_id: str, project_id: str, file_path: str
    ) -> bool:
        """
        Remove a link between a task and a file

        Args:
            task_id: UUID of the task
            project_id: UUID of the project
            file_path: Path to file relative to project root

        Returns:
            True if relationship was deleted, False otherwise
        """
        try:
            response = (
                await self.db.table("task_file_relationships")
                .delete()
                .eq("task_id", task_id)
                .eq("project_id", project_id)
                .eq("file_path", file_path)
                .execute()
            )

            logger.info(
                f"Unlinked task {task_id} from file {file_path}",
                extra={"task_id": task_id, "file_path": file_path},
            )

            return len(response.data) > 0

        except Exception as e:
            logger.error(
                f"Error unlinking task from file: {str(e)}",
                extra={"task_id": task_id, "file_path": file_path, "error": str(e)},
            )
            raise

    async def get_files_for_task(self, task_id: str) -> List[Dict[str, Any]]:
        """
        Get all files linked to a task

        Args:
            task_id: UUID of the task

        Returns:
            List of file relationship dicts
        """
        try:
            response = (
                await self.db.table("task_file_relationships")
                .select("*")
                .eq("task_id", task_id)
                .order("created_at", desc=True)
                .execute()
            )

            logger.debug(
                f"Retrieved {len(response.data)} files for task {task_id}",
                extra={"task_id": task_id, "count": len(response.data)},
            )

            return response.data

        except Exception as e:
            logger.error(
                f"Error getting files for task: {str(e)}",
                extra={"task_id": task_id, "error": str(e)},
            )
            raise

    async def get_tasks_for_file(
        self, project_id: str, file_path: str
    ) -> List[Dict[str, Any]]:
        """
        Get all tasks linked to a specific file

        Args:
            project_id: UUID of the project
            file_path: Path to file relative to project root

        Returns:
            List of task relationship dicts
        """
        try:
            response = (
                await self.db.table("task_file_relationships")
                .select("*")
                .eq("project_id", project_id)
                .eq("file_path", file_path)
                .order("created_at", desc=True)
                .execute()
            )

            logger.debug(
                f"Retrieved {len(response.data)} tasks for file {file_path}",
                extra={"file_path": file_path, "count": len(response.data)},
            )

            return response.data

        except Exception as e:
            logger.error(
                f"Error getting tasks for file: {str(e)}",
                extra={"file_path": file_path, "error": str(e)},
            )
            raise

    async def detect_relationships_from_commit(
        self, project_id: str, commit_message: str, changed_files: List[str]
    ) -> List[Dict[str, Any]]:
        """
        Auto-detect task-file relationships from commit message

        Parses commit message for task references and links changed files to those tasks.

        Args:
            project_id: UUID of the project
            commit_message: Git commit message
            changed_files: List of file paths changed in the commit

        Returns:
            List of created relationships
        """
        try:
            relationships = []

            # Patterns to detect task references
            patterns = [
                r"Task[:\s]+([a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12})",  # Task: uuid
                r"Fixes[:\s]+([a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12})",  # Fixes: uuid
                r"Implements[:\s]+([a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12})",  # Implements: uuid
                r"Task\s+#(\d+)",  # Task #123
                r"#(\d+)",  # #123
            ]

            # Find all task references
            task_refs = set()
            for pattern in patterns:
                matches = re.finditer(pattern, commit_message, re.IGNORECASE)
                for match in matches:
                    task_refs.add(match.group(1))

            if not task_refs:
                logger.debug("No task references found in commit message")
                return []

            # Determine relationship type from commit message
            relationship_type = "implements"
            if re.search(r"\btest\b|\btests\b|\btesting\b", commit_message, re.IGNORECASE):
                relationship_type = "tests"
            elif re.search(r"\bdoc\b|\bdocs\b|\bdocument\b", commit_message, re.IGNORECASE):
                relationship_type = "documents"
            elif re.search(r"\bfix\b|\bfixes\b|\bfixed\b", commit_message, re.IGNORECASE):
                relationship_type = "implements"
            elif re.search(r"\bref\b|\breference\b|\breferences\b", commit_message, re.IGNORECASE):
                relationship_type = "references"

            # Calculate confidence based on pattern match
            confidence = 0.9 if any(re.search(p, commit_message, re.IGNORECASE) for p in patterns[:3]) else 0.7

            # Link changed files to detected tasks
            for task_ref in task_refs:
                # Validate task exists
                try:
                    # Check if task_ref is UUID format
                    UUID(task_ref)
                    task_id = task_ref
                except ValueError:
                    # If numeric, skip (would need task number lookup)
                    logger.debug(f"Skipping numeric task reference: {task_ref}")
                    continue

                for file_path in changed_files:
                    try:
                        relationship = await self.link_task_to_file(
                            task_id=task_id,
                            project_id=project_id,
                            file_path=file_path,
                            relationship_type=relationship_type,
                            confidence=confidence,
                            created_by="git-hook",
                        )
                        relationships.append(relationship)
                    except Exception as e:
                        # Log but continue (relationship may already exist)
                        logger.warning(
                            f"Could not link task {task_id} to file {file_path}: {str(e)}"
                        )

            logger.info(
                f"Auto-detected {len(relationships)} task-file relationships from commit",
                extra={"project_id": project_id, "relationships_count": len(relationships)},
            )

            return relationships

        except Exception as e:
            logger.error(
                f"Error detecting relationships from commit: {str(e)}",
                extra={"project_id": project_id, "error": str(e)},
            )
            raise
