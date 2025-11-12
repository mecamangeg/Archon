"""
Sync Analytics API Routes
Phase 5, Task 5.6
API endpoints for sync analytics and metrics
"""

from typing import Dict
from fastapi import APIRouter, HTTPException, Query, Depends
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


# ============================================================================
# API Endpoints
# ============================================================================

@router.get("/projects/{project_id}/analytics/sync-history")
async def get_sync_history(
    project_id: str,
    days: int = Query(30, ge=1, le=365, description="Number of days to look back"),
    analytics_service = Depends()  # Inject SyncAnalyticsService
) -> Dict:
    """
    Get sync operation history for a project.

    **Query Parameters**:
    - `days`: Number of days to look back (1-365, default 30)

    **Response**:
    ```json
    {
        "project_id": "uuid",
        "days": 30,
        "operations": [
            {
                "id": "uuid",
                "trigger": "manual",
                "started_at": "2024-11-12T10:00:00Z",
                "completed_at": "2024-11-12T10:02:30Z",
                "status": "success",
                "files_processed": 120,
                "chunks_added": 450,
                "chunks_modified": 50,
                "chunks_deleted": 20,
                "duration_seconds": 150.5
            }
        ]
    }
    ```
    """
    try:
        operations = await analytics_service.get_sync_history(project_id, days)

        return {
            "project_id": project_id,
            "days": days,
            "operations": operations
        }

    except Exception as e:
        logger.error(f"Failed to get sync history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/projects/{project_id}/analytics/performance")
async def get_performance_metrics(
    project_id: str,
    days: int = Query(30, ge=1, le=365, description="Number of days to analyze"),
    analytics_service = Depends()  # Inject SyncAnalyticsService
) -> Dict:
    """
    Get performance metrics for a project.

    **Query Parameters**:
    - `days`: Number of days to analyze (1-365, default 30)

    **Response**:
    ```json
    {
        "project_id": "uuid",
        "days": 30,
        "metrics": {
            "total_syncs": 45,
            "successful_syncs": 43,
            "failed_syncs": 2,
            "average_duration": 125.5,
            "total_files_processed": 5400,
            "total_chunks_added": 18500,
            "total_chunks_modified": 2300,
            "total_chunks_deleted": 450,
            "success_rate": 95.6,
            "syncs_by_trigger": {
                "manual": 12,
                "git-hook": 20,
                "realtime": 13
            }
        }
    }
    ```
    """
    try:
        metrics = await analytics_service.get_performance_metrics(project_id, days)

        return {
            "project_id": project_id,
            "days": days,
            "metrics": metrics
        }

    except Exception as e:
        logger.error(f"Failed to get performance metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/projects/{project_id}/analytics/errors")
async def get_error_statistics(
    project_id: str,
    days: int = Query(30, ge=1, le=365, description="Number of days to analyze"),
    analytics_service = Depends()  # Inject SyncAnalyticsService
) -> Dict:
    """
    Get error statistics for a project.

    **Query Parameters**:
    - `days`: Number of days to analyze (1-365, default 30)

    **Response**:
    ```json
    {
        "project_id": "uuid",
        "days": 30,
        "statistics": {
            "total_errors": 5,
            "error_rate": 10.0,
            "errors_by_trigger": {
                "git-hook": 3,
                "realtime": 2
            },
            "common_errors": [
                {
                    "message": "Connection timeout to embedding service",
                    "count": 3
                },
                {
                    "message": "Invalid file path: permission denied",
                    "count": 2
                }
            ]
        }
    }
    ```
    """
    try:
        statistics = await analytics_service.get_error_statistics(project_id, days)

        return {
            "project_id": project_id,
            "days": days,
            "statistics": statistics
        }

    except Exception as e:
        logger.error(f"Failed to get error statistics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/projects/{project_id}/analytics/growth")
async def get_growth_metrics(
    project_id: str,
    days: int = Query(30, ge=1, le=365, description="Number of days to analyze"),
    analytics_service = Depends()  # Inject SyncAnalyticsService
) -> Dict:
    """
    Get growth metrics for a project.

    **Query Parameters**:
    - `days`: Number of days to analyze (1-365, default 30)

    **Response**:
    ```json
    {
        "project_id": "uuid",
        "days": 30,
        "metrics": {
            "growth_by_date": [
                {
                    "date": "2024-11-01",
                    "files_processed": 120,
                    "chunks_added": 450,
                    "chunks_modified": 50,
                    "chunks_deleted": 20,
                    "syncs_count": 3
                }
            ],
            "cumulative_files": 5400,
            "cumulative_chunks": 18500
        }
    }
    ```
    """
    try:
        metrics = await analytics_service.get_growth_metrics(project_id, days)

        return {
            "project_id": project_id,
            "days": days,
            "metrics": metrics
        }

    except Exception as e:
        logger.error(f"Failed to get growth metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Health Check
# ============================================================================

@router.get("/analytics/health")
async def analytics_health_check() -> Dict:
    """
    Health check for analytics endpoints.

    Returns:
        Status message indicating API is operational
    """
    return {
        "status": "healthy",
        "service": "Sync Analytics API",
        "endpoints": ["sync-history", "performance", "errors", "growth"]
    }
