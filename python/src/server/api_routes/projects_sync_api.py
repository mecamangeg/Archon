"""
Project Sync API Routes
Phase 1, Task 1.3
API endpoints for managing project sync configuration
"""

from typing import Optional, List, Dict
from datetime import datetime
from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel, Field
import uuid
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


# ============================================================================
# Request/Response Models
# ============================================================================

class UpdateSyncConfigRequest(BaseModel):
    """Request model for updating project sync configuration"""
    local_path: Optional[str] = Field(None, description="Absolute path to project directory")
    sync_mode: Optional[str] = Field(None, description="Sync mode: manual, realtime, periodic, git-hook")
    auto_sync_enabled: Optional[bool] = Field(None, description="Enable automatic sync")

    class Config:
        schema_extra = {
            "example": {
                "local_path": "/home/user/projects/my-app",
                "sync_mode": "realtime",
                "auto_sync_enabled": True
            }
        }


class TriggerSyncRequest(BaseModel):
    """Request model for manually triggering sync"""
    trigger: str = Field("manual", description="Trigger source: manual, git-hook, scheduled")
    changed_files: Optional[List[str]] = Field(None, description="Specific files to sync (optional)")

    class Config:
        schema_extra = {
            "example": {
                "trigger": "manual",
                "changed_files": ["src/api/auth.ts", "src/components/Login.tsx"]
            }
        }


class SyncConfigResponse(BaseModel):
    """Response for sync configuration operations"""
    success: bool
    project_id: str
    config: Dict


class SyncStatusResponse(BaseModel):
    """Response for sync status queries"""
    project_id: str
    sync_status: str
    last_sync_at: Optional[str]
    auto_sync_enabled: bool
    sync_mode: str
    local_path: Optional[str]
    last_sync_error: Optional[str]
    stats: Dict


class TriggerSyncResponse(BaseModel):
    """Response for sync trigger operations"""
    success: bool
    sync_job_id: str
    status: str
    message: Optional[str] = None
    trigger: str
    stats: Optional[Dict] = None


# ============================================================================
# API Endpoints
# ============================================================================

@router.put("/projects/{project_id}/sync/config", response_model=SyncConfigResponse)
async def update_project_sync_config(
    project_id: str,
    request: UpdateSyncConfigRequest,
    project_service = Depends()  # Inject project_service dependency
) -> Dict:
    """
    Update sync configuration for a project.

    **Request Body**:
    - `local_path`: Absolute path to project directory
    - `sync_mode`: 'manual', 'realtime', 'periodic', or 'git-hook'
    - `auto_sync_enabled`: Enable/disable automatic sync

    **Response**:
    ```json
    {
        "success": true,
        "project_id": "uuid",
        "config": {
            "local_path": "/path/to/project",
            "sync_mode": "realtime",
            "auto_sync_enabled": true
        }
    }
    ```

    **Errors**:
    - 400: Invalid local_path or sync_mode
    - 404: Project not found
    - 500: Server error
    """
    try:
        updated = await project_service.update_project_sync_config(
            project_id=project_id,
            local_path=request.local_path,
            sync_mode=request.sync_mode,
            auto_sync_enabled=request.auto_sync_enabled
        )

        logger.info(f"Sync config updated for project {project_id}")

        return {
            "success": True,
            "project_id": project_id,
            "config": {
                "local_path": updated.get('local_path'),
                "sync_mode": updated.get('sync_mode'),
                "auto_sync_enabled": updated.get('auto_sync_enabled'),
                "sync_status": updated.get('sync_status')
            }
        }

    except ValueError as e:
        logger.error(f"Invalid sync config: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to update sync config: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/projects/{project_id}/sync/status", response_model=SyncStatusResponse)
async def get_project_sync_status(
    project_id: str,
    project_service = Depends(),
    knowledge_service = Depends()  # For Phase 2 stats
) -> Dict:
    """
    Get current sync status for a project.

    **Response**:
    ```json
    {
        "project_id": "uuid",
        "sync_status": "synced",
        "last_sync_at": "2024-11-12T10:30:00Z",
        "auto_sync_enabled": true,
        "sync_mode": "realtime",
        "local_path": "/path/to/project",
        "stats": {
            "total_files": 120,
            "total_chunks": 1850,
            "last_sync_duration_seconds": 3.5
        }
    }
    ```
    """
    try:
        # Get project
        project = await project_service.get_project(project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        # Get codebase stats (Phase 2: Real stats from codebase source)
        stats = {
            "total_files": 0,
            "total_chunks": 0,
            "last_sync_duration_seconds": 0
        }

        # Phase 2: Get real stats from codebase source
        if project.get('codebase_source_id'):
            from ..services.knowledge.codebase_source_service import CodebaseSourceService
            codebase_service = CodebaseSourceService(supabase_client)
            stats = await codebase_service.get_source_stats(
                project['codebase_source_id']
            )

        return {
            "project_id": project_id,
            "sync_status": project.get('sync_status', 'never_synced'),
            "last_sync_at": project.get('last_sync_at'),
            "auto_sync_enabled": project.get('auto_sync_enabled', False),
            "sync_mode": project.get('sync_mode', 'manual'),
            "local_path": project.get('local_path'),
            "last_sync_error": project.get('last_sync_error'),
            "stats": stats
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get sync status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/projects/{project_id}/sync", response_model=TriggerSyncResponse)
async def trigger_project_sync(
    project_id: str,
    request: TriggerSyncRequest = TriggerSyncRequest(),
    project_service = Depends(),
    supabase_client = Depends(),
    embedding_service = Depends(),
    codebase_source_service = Depends()
) -> Dict:
    """
    Manually trigger synchronization for a project.

    **Request Body**:
    - `trigger`: Source of trigger ('manual', 'git-hook', 'scheduled')
    - `changed_files`: Optional list of specific files to sync

    **Response**:
    ```json
    {
        "success": true,
        "sync_job_id": "uuid",
        "status": "completed",
        "trigger": "manual",
        "stats": {
            "files_processed": 120,
            "chunks_added": 450,
            "chunks_modified": 50,
            "chunks_deleted": 20,
            "duration_seconds": 15.3,
            "errors": []
        }
    }
    ```

    **Phase 2**: Performs actual incremental sync with real stats
    """
    try:
        # Get project
        project = await project_service.get_project(project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        if not project.get('local_path'):
            raise HTTPException(
                status_code=400,
                detail="Project has no local_path configured. Please set local_path first."
            )

        # Phase 2: Perform actual sync
        from ..services.sync.incremental_sync_service import IncrementalSyncService

        sync_service = IncrementalSyncService(
            db=supabase_client,
            embedding_service=embedding_service,
            project_service=project_service,
            codebase_source_service=codebase_source_service
        )

        # Execute sync
        stats = await sync_service.sync_project_changes(
            project_id=project_id,
            changed_files=request.changed_files
        )

        sync_job_id = str(uuid.uuid4())

        logger.info(
            f"Sync completed for project {project_id} - "
            f"{stats.files_processed} files, {stats.duration_seconds:.2f}s"
        )

        return {
            "success": True,
            "sync_job_id": sync_job_id,
            "status": "completed",
            "trigger": request.trigger,
            "stats": {
                "files_processed": stats.files_processed,
                "chunks_added": stats.chunks_added,
                "chunks_modified": stats.chunks_modified,
                "chunks_deleted": stats.chunks_deleted,
                "duration_seconds": round(stats.duration_seconds, 2),
                "errors": stats.errors
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to trigger sync: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Health Check
# ============================================================================

@router.get("/projects/sync/health")
async def sync_health_check() -> Dict:
    """
    Health check for sync endpoints.

    Returns:
        Status message indicating API is operational
    """
    return {
        "status": "healthy",
        "service": "Project Sync API",
        "phase": "1",
        "features": ["config", "status", "trigger"]
    }
