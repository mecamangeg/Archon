"""
Task File API Routes for Archon
Phase 5, Task 5.1

FastAPI endpoints for managing task-file relationships.
"""

from typing import List, Optional
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from src.server.config.logfire_config import get_logger
from src.server.services.tasks.task_file_service import TaskFileService
from src.server.utils import get_supabase_client

logger = get_logger(__name__)
router = APIRouter(prefix="/tasks", tags=["task-files"])


# Pydantic models
class LinkFileRequest(BaseModel):
    """Request model for linking file to task"""

    project_id: str = Field(..., description="UUID of the project")
    file_path: str = Field(..., description="Path to file relative to project root")
    relationship_type: str = Field(
        default="implements",
        description="Type of relationship: implements, tests, documents, references",
    )
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Confidence score")
    created_by: str = Field(
        default="user", description="Source: user, auto, git-hook"
    )


class UnlinkFileRequest(BaseModel):
    """Request model for unlinking file from task"""

    project_id: str = Field(..., description="UUID of the project")
    file_path: str = Field(..., description="Path to file relative to project root")


class FileRelationship(BaseModel):
    """Response model for file relationship"""

    id: str
    task_id: str
    project_id: str
    file_path: str
    relationship_type: str
    confidence: float
    created_at: str
    created_by: str


@router.post("/{task_id}/files", response_model=FileRelationship)
async def link_file_to_task(task_id: str, request: LinkFileRequest):
    """
    Link a file to a task

    Args:
        task_id: UUID of the task
        request: LinkFileRequest containing project_id and file_path

    Returns:
        Created file relationship

    Raises:
        HTTPException: If linking fails
    """
    try:
        db = get_supabase_client()
        service = TaskFileService(db)

        relationship = await service.link_task_to_file(
            task_id=task_id,
            project_id=request.project_id,
            file_path=request.file_path,
            relationship_type=request.relationship_type,
            confidence=request.confidence,
            created_by=request.created_by,
        )

        return relationship

    except ValueError as e:
        logger.error(f"Validation error linking file: {str(e)}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Error linking file to task: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to link file to task: {str(e)}",
        )


@router.delete("/{task_id}/files", status_code=status.HTTP_204_NO_CONTENT)
async def unlink_file_from_task(task_id: str, request: UnlinkFileRequest):
    """
    Unlink a file from a task

    Args:
        task_id: UUID of the task
        request: UnlinkFileRequest containing project_id and file_path

    Raises:
        HTTPException: If unlinking fails
    """
    try:
        db = get_supabase_client()
        service = TaskFileService(db)

        success = await service.unlink_task_from_file(
            task_id=task_id,
            project_id=request.project_id,
            file_path=request.file_path,
        )

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Relationship not found",
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error unlinking file from task: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to unlink file from task: {str(e)}",
        )


@router.get("/{task_id}/files", response_model=List[FileRelationship])
async def get_files_for_task(task_id: str):
    """
    Get all files linked to a task

    Args:
        task_id: UUID of the task

    Returns:
        List of file relationships

    Raises:
        HTTPException: If query fails
    """
    try:
        db = get_supabase_client()
        service = TaskFileService(db)

        files = await service.get_files_for_task(task_id)
        return files

    except Exception as e:
        logger.error(f"Error getting files for task: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get files for task: {str(e)}",
        )


# Note: Path parameter with slashes requires special handling
@router.get("/projects/{project_id}/files/{file_path:path}/tasks", response_model=List[FileRelationship])
async def get_tasks_for_file(project_id: str, file_path: str):
    """
    Get all tasks linked to a specific file

    Args:
        project_id: UUID of the project
        file_path: Path to file relative to project root (supports slashes)

    Returns:
        List of task relationships

    Raises:
        HTTPException: If query fails
    """
    try:
        db = get_supabase_client()
        service = TaskFileService(db)

        tasks = await service.get_tasks_for_file(project_id, file_path)
        return tasks

    except Exception as e:
        logger.error(f"Error getting tasks for file: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get tasks for file: {str(e)}",
        )
