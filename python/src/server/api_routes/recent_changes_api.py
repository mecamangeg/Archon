"""
Recent Changes API Routes for Archon
Phase 5, Task 5.4

FastAPI endpoints for querying recent file changes.
"""

from typing import Any, Dict, Optional
from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel

from src.server.config.logfire_config import get_logger
from src.server.services.search.recent_changes_service import RecentChangesService
from src.server.utils import get_supabase_client

logger = get_logger(__name__)
router = APIRouter(prefix="/projects", tags=["recent-changes"])


# Pydantic models
class ChangeStatistics(BaseModel):
    """Response model for change statistics"""

    total_files_changed: int
    total_chunks_updated: int
    language_breakdown: Dict[str, int]
    changes_by_date: Dict[str, int]
    period_days: int


@router.get("/{project_id}/changes/recent")
async def get_recent_changes(
    project_id: str,
    days: int = Query(default=7, ge=1, le=90, description="Number of days to look back"),
    file_filter: Optional[str] = Query(
        default=None, description="Optional file pattern filter"
    ),
):
    """
    Get files that changed recently in a project

    Args:
        project_id: UUID of the project
        days: Number of days to look back (1-90)
        file_filter: Optional file pattern filter

    Returns:
        List of recently changed files

    Raises:
        HTTPException: If query fails
    """
    try:
        db = get_supabase_client()
        service = RecentChangesService(db)

        results = await service.get_recent_changes(
            project_id=project_id,
            days=days,
            file_filter=file_filter,
        )

        return results

    except ValueError as e:
        logger.error(f"Validation error getting recent changes: {str(e)}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Error getting recent changes: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get recent changes: {str(e)}",
        )


@router.get("/{project_id}/changes/stats", response_model=ChangeStatistics)
async def get_change_statistics(
    project_id: str,
    days: int = Query(
        default=30, ge=1, le=365, description="Number of days to analyze"
    ),
):
    """
    Get statistics about recent changes in a project

    Args:
        project_id: UUID of the project
        days: Number of days to analyze (1-365)

    Returns:
        Change statistics

    Raises:
        HTTPException: If query fails
    """
    try:
        db = get_supabase_client()
        service = RecentChangesService(db)

        stats = await service.get_change_statistics(project_id=project_id, days=days)

        return stats

    except ValueError as e:
        logger.error(f"Validation error getting statistics: {str(e)}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Error getting change statistics: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get change statistics: {str(e)}",
        )
