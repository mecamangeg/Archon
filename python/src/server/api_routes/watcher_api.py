"""
API routes for file watcher lifecycle management.

Provides endpoints to control file watchers, check status, and monitor
health of the background sync worker.
"""

import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from src.server.services.sync.sync_worker import SyncWorker
from src.server.services.sync.file_watcher import FileWatcherService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/watcher", tags=["watcher"])


# Global worker instance (set by main application)
_worker_instance: Optional[SyncWorker] = None


def set_worker_instance(worker: SyncWorker) -> None:
    """
    Set the global worker instance.

    Should be called by main application during startup.

    Args:
        worker: SyncWorker instance to use for API endpoints
    """
    global _worker_instance
    _worker_instance = worker


def get_worker() -> SyncWorker:
    """
    Dependency to get worker instance.

    Returns:
        SyncWorker instance

    Raises:
        HTTPException: If worker not initialized
    """
    if _worker_instance is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Sync worker not initialized"
        )
    return _worker_instance


# Request/Response Models

class StartWatcherRequest(BaseModel):
    """Request to start watcher for a project."""
    local_path: str = Field(..., description="Local file system path to monitor")


class WatcherStatusResponse(BaseModel):
    """Response with watcher status for a project."""
    project_id: str
    is_active: bool
    is_watching: bool


class WatcherHealthResponse(BaseModel):
    """Response with worker health information."""
    healthy: bool
    running: bool
    watched_projects: int
    pending_events: int
    last_heartbeat: Optional[str]


class ErrorResponse(BaseModel):
    """Error response model."""
    detail: str


# API Endpoints

@router.post(
    "/projects/{project_id}/start",
    response_model=WatcherStatusResponse,
    status_code=status.HTTP_200_OK,
    responses={
        404: {"model": ErrorResponse},
        500: {"model": ErrorResponse}
    }
)
async def start_watcher(
    project_id: str,
    request: StartWatcherRequest,
    worker: SyncWorker = Depends(get_worker)
) -> WatcherStatusResponse:
    """
    Start file watcher for a project.

    Args:
        project_id: Unique project identifier
        request: Request with local path
        worker: Worker instance from dependency

    Returns:
        Watcher status response

    Raises:
        HTTPException: If watcher fails to start
    """
    try:
        logger.info(f"Starting watcher for project {project_id}")

        success = await worker.file_watcher.start_watching(
            project_id, request.local_path
        )

        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to start watcher"
            )

        # Add to watched projects set
        worker.watched_projects.add(project_id)

        is_watching = worker.file_watcher.is_watching(project_id)

        return WatcherStatusResponse(
            project_id=project_id,
            is_active=True,
            is_watching=is_watching
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error starting watcher for project {project_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post(
    "/projects/{project_id}/stop",
    response_model=WatcherStatusResponse,
    status_code=status.HTTP_200_OK,
    responses={
        404: {"model": ErrorResponse},
        500: {"model": ErrorResponse}
    }
)
async def stop_watcher(
    project_id: str,
    worker: SyncWorker = Depends(get_worker)
) -> WatcherStatusResponse:
    """
    Stop file watcher for a project.

    Args:
        project_id: Unique project identifier
        worker: Worker instance from dependency

    Returns:
        Watcher status response

    Raises:
        HTTPException: If watcher fails to stop
    """
    try:
        logger.info(f"Stopping watcher for project {project_id}")

        success = await worker.file_watcher.stop_watching(project_id)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to stop watcher"
            )

        # Remove from watched projects set
        worker.watched_projects.discard(project_id)

        is_watching = worker.file_watcher.is_watching(project_id)

        return WatcherStatusResponse(
            project_id=project_id,
            is_active=False,
            is_watching=is_watching
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error stopping watcher for project {project_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get(
    "/projects/{project_id}/status",
    response_model=WatcherStatusResponse,
    status_code=status.HTTP_200_OK,
    responses={
        404: {"model": ErrorResponse}
    }
)
async def get_watcher_status(
    project_id: str,
    worker: SyncWorker = Depends(get_worker)
) -> WatcherStatusResponse:
    """
    Get watcher status for a project.

    Args:
        project_id: Unique project identifier
        worker: Worker instance from dependency

    Returns:
        Watcher status response
    """
    is_watching = worker.file_watcher.is_watching(project_id)
    is_active = project_id in worker.watched_projects

    return WatcherStatusResponse(
        project_id=project_id,
        is_active=is_active,
        is_watching=is_watching
    )


@router.get(
    "/health",
    response_model=WatcherHealthResponse,
    status_code=status.HTTP_200_OK
)
async def watcher_health(
    worker: SyncWorker = Depends(get_worker)
) -> WatcherHealthResponse:
    """
    Health check for sync worker.

    Args:
        worker: Worker instance from dependency

    Returns:
        Health status response
    """
    status_info = worker.get_status()
    healthy = worker.is_healthy()

    return WatcherHealthResponse(
        healthy=healthy,
        running=status_info["running"],
        watched_projects=status_info["watched_projects"],
        pending_events=status_info["pending_events"],
        last_heartbeat=status_info["last_heartbeat"]
    )
