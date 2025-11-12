"""
Project Search API Routes for Archon
Phase 5, Task 5.3

FastAPI endpoints for project-scoped code search.
"""

from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field

from src.server.config.logfire_config import get_logger
from src.server.services.search.project_code_search import ProjectCodeSearchService
from src.server.utils import get_supabase_client

logger = get_logger(__name__)
router = APIRouter(prefix="/projects", tags=["project-search"])


# Pydantic models
class SearchCodeRequest(BaseModel):
    """Request model for code search"""

    query: str = Field(..., description="Search query (semantic search)")
    match_count: int = Field(default=5, ge=1, le=50, description="Number of results")
    file_filter: Optional[str] = Field(
        default=None, description="File pattern filter (e.g., '*.py')"
    )
    language_filter: Optional[str] = Field(
        default=None, description="Language filter (e.g., 'python')"
    )
    recency_days: Optional[int] = Field(
        default=None, ge=1, description="Filter files modified in last N days"
    )


class SearchResult(BaseModel):
    """Response model for search result"""

    id: str
    file_path: str
    chunk_index: int
    content: str
    start_line: Optional[int] = None
    end_line: Optional[int] = None
    language: Optional[str] = None
    updated_at: str
    similarity: float


class RecentChange(BaseModel):
    """Response model for recent change"""

    file_path: str
    language: Optional[str]
    last_updated: str
    chunk_count: int


@router.post("/{project_id}/search/code", response_model=List[SearchResult])
async def search_project_code(project_id: str, request: SearchCodeRequest):
    """
    Search code within a project's codebase

    Args:
        project_id: UUID of the project
        request: SearchCodeRequest with query and filters

    Returns:
        List of search results

    Raises:
        HTTPException: If search fails
    """
    try:
        db = get_supabase_client()
        service = ProjectCodeSearchService(db)

        results = await service.search(
            project_id=project_id,
            query=request.query,
            match_count=request.match_count,
            file_filter=request.file_filter,
            language_filter=request.language_filter,
            recency_days=request.recency_days,
        )

        return results

    except ValueError as e:
        logger.error(f"Validation error searching code: {str(e)}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Error searching project code: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to search project code: {str(e)}",
        )


@router.get("/{project_id}/search/recent-changes", response_model=List[RecentChange])
async def get_recent_changes(
    project_id: str,
    days: int = Query(default=7, ge=1, le=90, description="Number of days to look back"),
):
    """
    Get files that changed recently in a project

    Args:
        project_id: UUID of the project
        days: Number of days to look back (1-90)

    Returns:
        List of recently changed files

    Raises:
        HTTPException: If query fails
    """
    try:
        db = get_supabase_client()
        service = ProjectCodeSearchService(db)

        results = await service.get_recent_changes(project_id=project_id, days=days)

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
