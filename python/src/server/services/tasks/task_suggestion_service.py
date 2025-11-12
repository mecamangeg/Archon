"""
Task Suggestion Service for Archon
Phase 5, Task 5.5

Service for suggesting task updates and new tasks based on file changes.
"""

from typing import Any, Dict, List
from src.server.config.logfire_config import get_logger
from src.server.services.tasks.task_file_service import TaskFileService

logger = get_logger(__name__)


class TaskSuggestionService:
    """Service for generating task suggestions from file changes"""

    def __init__(self, db):
        """
        Initialize TaskSuggestionService

        Args:
            db: Supabase client instance
        """
        self.db = db
        self.task_file_service = TaskFileService(db)

    async def suggest_task_updates(
        self, project_id: str, changed_files: List[str], commit_message: str
    ) -> List[Dict[str, Any]]:
        """
        Suggest task updates based on file changes

        Args:
            project_id: UUID of the project
            changed_files: List of file paths that changed
            commit_message: Git commit message

        Returns:
            List of suggested task updates
        """
        try:
            suggestions = []

            # Find tasks linked to changed files
            for file_path in changed_files:
                tasks = await self.task_file_service.get_tasks_for_file(
                    project_id, file_path
                )

                for task_relationship in tasks:
                    task_id = task_relationship["task_id"]

                    # Get task details
                    task_response = (
                        await self.db.table("tasks")
                        .select("*")
                        .eq("id", task_id)
                        .execute()
                    )

                    if not task_response.data:
                        continue

                    task = task_response.data[0]

                    # Determine suggested action based on task status
                    current_status = task.get("status", "todo")
                    suggested_action = None
                    confidence = 0.8

                    if current_status == "todo":
                        suggested_action = "Mark task as 'doing' (work has started)"
                        confidence = 0.9
                    elif current_status == "doing":
                        # Check if commit message suggests completion
                        if any(
                            keyword in commit_message.lower()
                            for keyword in ["fix", "implement", "complete", "done"]
                        ):
                            suggested_action = (
                                "Mark task as 'done' (work appears complete)"
                            )
                            confidence = 0.7
                        else:
                            suggested_action = "Update task progress (work continuing)"
                            confidence = 0.6
                    elif current_status == "done":
                        suggested_action = "Review: task marked done but files modified"
                        confidence = 0.5

                    suggestion = {
                        "type": "update_task",
                        "task_id": task_id,
                        "task_title": task.get("title"),
                        "current_status": current_status,
                        "file_path": file_path,
                        "reason": f"File {file_path} was modified",
                        "confidence": confidence,
                        "suggested_action": suggested_action,
                        "commit_message": commit_message,
                    }

                    suggestions.append(suggestion)

            logger.info(
                f"Generated {len(suggestions)} task update suggestions",
                extra={
                    "project_id": project_id,
                    "changed_files_count": len(changed_files),
                },
            )

            return suggestions

        except Exception as e:
            logger.error(f"Error suggesting task updates: {str(e)}")
            raise

    async def suggest_new_tasks(
        self, project_id: str, changed_files: List[str]
    ) -> List[Dict[str, Any]]:
        """
        Suggest new tasks for unlinked files

        Args:
            project_id: UUID of the project
            changed_files: List of file paths that changed

        Returns:
            List of suggestions for new tasks
        """
        try:
            suggestions = []

            # Find files without linked tasks
            for file_path in changed_files:
                tasks = await self.task_file_service.get_tasks_for_file(
                    project_id, file_path
                )

                if len(tasks) == 0:
                    # File has no linked tasks
                    confidence = 0.6

                    # Boost confidence for certain file types
                    if file_path.endswith((".py", ".ts", ".tsx", ".js", ".jsx")):
                        confidence = 0.7
                    if "test" in file_path.lower():
                        confidence = 0.5  # Lower for test files

                    # Generate suggested task title
                    file_name = file_path.split("/")[-1]
                    suggested_title = f"Update {file_name}"

                    # Detect file type for better description
                    if "test" in file_path.lower():
                        suggested_description = f"Tests updated in {file_path}"
                    elif file_path.endswith((".md", ".txt", ".rst")):
                        suggested_description = f"Documentation updated in {file_path}"
                    else:
                        suggested_description = f"Changes detected in {file_path}"

                    suggestion = {
                        "type": "create_task",
                        "file_path": file_path,
                        "reason": f"New or modified file without linked task: {file_path}",
                        "confidence": confidence,
                        "suggested_title": suggested_title,
                        "suggested_description": suggested_description,
                        "suggested_status": "doing",
                    }

                    suggestions.append(suggestion)

            logger.info(
                f"Generated {len(suggestions)} new task suggestions",
                extra={
                    "project_id": project_id,
                    "unlinked_files": len(suggestions),
                },
            )

            return suggestions

        except Exception as e:
            logger.error(f"Error suggesting new tasks: {str(e)}")
            raise

    async def get_suggestions_for_commit(
        self, project_id: str, commit_sha: str
    ) -> List[Dict[str, Any]]:
        """
        Get task suggestions for a specific commit

        Note: This requires commit data to be stored in database.
        Placeholder implementation for future enhancement.

        Args:
            project_id: UUID of the project
            commit_sha: Git commit SHA

        Returns:
            List of task suggestions
        """
        try:
            # Placeholder - would query commit data from database
            # For now, return empty list
            logger.info(
                f"get_suggestions_for_commit called (placeholder)",
                extra={"project_id": project_id, "commit_sha": commit_sha},
            )

            return []

        except Exception as e:
            logger.error(f"Error getting suggestions for commit: {str(e)}")
            raise

    def _calculate_confidence(
        self,
        task_status: str,
        commit_message: str,
        file_path: str,
    ) -> float:
        """
        Calculate confidence score for a suggestion

        Args:
            task_status: Current task status
            commit_message: Commit message
            file_path: File path

        Returns:
            Confidence score (0.0-1.0)
        """
        confidence = 0.5  # Base confidence

        # Boost confidence based on status transitions
        if task_status == "todo":
            confidence += 0.3
        elif task_status == "doing":
            confidence += 0.2

        # Boost confidence if commit message is detailed
        if len(commit_message) > 50:
            confidence += 0.1

        # Boost confidence for source files
        if file_path.endswith((".py", ".ts", ".tsx", ".js", ".jsx")):
            confidence += 0.1

        # Cap at 1.0
        return min(confidence, 1.0)
