"""
Task Suggestion API Routes for Archon
Phase 5, Task 5.5

FastAPI endpoints for task suggestions based on file changes.
"""

from typing import List
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from src.server.config.logfire_config import get_logger
from src.server.services.tasks.task_suggestion_service import TaskSuggestionService
from src.server.utils import get_supabase_client

logger = get_logger(__name__)
router = APIRouter(prefix="/projects", tags=["task-suggestions"])


# Pydantic models
class SuggestionsRequest(BaseModel):
    """Request model for task suggestions"""

    changed_files: List[str] = Field(..., description="List of changed file paths")
    commit_message: str = Field(default="", description="Git commit message")


class TaskUpdateSuggestion(BaseModel):
    """Response model for task update suggestion"""

    type: str  # "update_task" or "create_task"
    task_id: str = None
    task_title: str = None
    current_status: str = None
    file_path: str
    reason: str
    confidence: float
    suggested_action: str = None
    suggested_title: str = None
    suggested_description: str = None
    suggested_status: str = None
    commit_message: str = None


@router.post("/{project_id}/tasks/suggestions", response_model=List[TaskUpdateSuggestion])
async def get_task_suggestions(project_id: str, request: SuggestionsRequest):
    """
    Get task suggestions based on file changes

    Analyzes changed files and suggests:
    - Updates to existing linked tasks
    - Creation of new tasks for unlinked files

    Args:
        project_id: UUID of the project
        request: SuggestionsRequest with changed files and commit message

    Returns:
        List of task suggestions

    Raises:
        HTTPException: If suggestion generation fails
    """
    try:
        db = get_supabase_client()
        service = TaskSuggestionService(db)

        # Get suggestions for linked tasks
        update_suggestions = await service.suggest_task_updates(
            project_id=project_id,
            changed_files=request.changed_files,
            commit_message=request.commit_message,
        )

        # Get suggestions for unlinked files
        new_task_suggestions = await service.suggest_new_tasks(
            project_id=project_id,
            changed_files=request.changed_files,
        )

        # Combine suggestions
        all_suggestions = update_suggestions + new_task_suggestions

        # Sort by confidence (highest first)
        all_suggestions.sort(key=lambda x: x["confidence"], reverse=True)

        logger.info(
            f"Generated {len(all_suggestions)} task suggestions",
            extra={
                "project_id": project_id,
                "update_suggestions": len(update_suggestions),
                "new_task_suggestions": len(new_task_suggestions),
            },
        )

        return all_suggestions

    except Exception as e:
        logger.error(f"Error generating task suggestions: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate task suggestions: {str(e)}",
        )
