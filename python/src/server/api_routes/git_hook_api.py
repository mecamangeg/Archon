"""
Git Hook Management API

FastAPI routes for installing, uninstalling, and checking git hooks.
Provides endpoints for managing git hooks in project repositories.
"""

import logging
from typing import Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel, Field

from server.services.sync.git_hook_installer import GitHookInstaller
from server.services.sync.hook_renderer import HookRenderer
from server.services.project_service import ProjectService

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/projects", tags=["git-hooks"])


# Pydantic Models

class GitHookInstallRequest(BaseModel):
    """Request model for installing a git hook."""

    archon_api_url: str = Field(
        ...,
        description="Base URL of the Archon API (e.g., http://localhost:8000)",
        example="http://localhost:8000"
    )
    chain_existing: bool = Field(
        default=True,
        description="Whether to chain with existing hooks"
    )


class GitHookInstallResponse(BaseModel):
    """Response model for git hook installation."""

    success: bool = Field(..., description="Whether installation was successful")
    message: str = Field(..., description="Human-readable status message")
    hook_path: Optional[str] = Field(None, description="Path to the installed hook")
    chained: Optional[bool] = Field(None, description="Whether hook was chained with existing hook")
    backup_created: Optional[bool] = Field(None, description="Whether a backup was created")
    installed_at: Optional[str] = Field(None, description="Timestamp of installation")


class GitHookUninstallRequest(BaseModel):
    """Request model for uninstalling a git hook."""

    restore_backup: bool = Field(
        default=True,
        description="Whether to restore backup if it exists"
    )


class GitHookUninstallResponse(BaseModel):
    """Response model for git hook uninstallation."""

    success: bool = Field(..., description="Whether uninstallation was successful")
    message: str = Field(..., description="Human-readable status message")
    hook_path: Optional[str] = Field(None, description="Path to the uninstalled hook")
    backup_restored: Optional[bool] = Field(None, description="Whether backup was restored")
    uninstalled_at: Optional[str] = Field(None, description="Timestamp of uninstallation")


class GitHookStatusResponse(BaseModel):
    """Response model for git hook status."""

    installed: bool = Field(..., description="Whether hook is installed")
    hook_path: Optional[str] = Field(None, description="Path to the hook file")
    has_backup: Optional[bool] = Field(None, description="Whether a backup exists")
    is_archon_hook: Optional[bool] = Field(None, description="Whether this is an Archon hook")
    size_bytes: Optional[int] = Field(None, description="Size of hook file in bytes")
    modified_at: Optional[str] = Field(None, description="Last modification timestamp")


# Dependency Injection

def get_hook_installer() -> GitHookInstaller:
    """Dependency for GitHookInstaller."""
    return GitHookInstaller()


def get_hook_renderer() -> HookRenderer:
    """Dependency for HookRenderer."""
    return HookRenderer()


def get_project_service() -> ProjectService:
    """Dependency for ProjectService."""
    # TODO: Replace with actual ProjectService instance from DI container
    return ProjectService()


# API Endpoints

@router.post(
    "/{project_id}/git-hook/install",
    response_model=GitHookInstallResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Install git hook for project",
    description="Install a post-commit git hook in the project repository"
)
async def install_git_hook(
    project_id: str,
    request: GitHookInstallRequest,
    installer: GitHookInstaller = Depends(get_hook_installer),
    renderer: HookRenderer = Depends(get_hook_renderer),
    project_service: ProjectService = Depends(get_project_service)
) -> GitHookInstallResponse:
    """
    Install a post-commit git hook in the project repository.

    The hook will:
    - Detect files changed in each commit
    - Trigger sync via Archon API
    - Never block commits (always exits with code 0)

    Args:
        project_id: UUID of the project
        request: Installation configuration
        installer: GitHookInstaller dependency
        renderer: HookRenderer dependency
        project_service: ProjectService dependency

    Returns:
        Installation status and details

    Raises:
        HTTPException: If installation fails
    """
    try:
        # Get project from database
        project = await project_service.get_project(project_id)

        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project not found: {project_id}"
            )

        # Check if project has local_path
        if not project.get("local_path"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Project does not have a local_path configured"
            )

        local_path = project["local_path"]

        # Validate that it's a git repository
        if not await installer.validate_git_repo(local_path):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Not a valid git repository: {local_path}"
            )

        # Render hook template
        hook_content = await renderer.render_post_commit_hook(
            project_id=project_id,
            archon_api_url=request.archon_api_url
        )

        # Install the hook
        result = await installer.install_hook(
            repo_path=local_path,
            hook_name="post-commit",
            hook_content=hook_content,
            chain_existing=request.chain_existing
        )

        logger.info(f"Installed git hook for project {project_id}")

        return GitHookInstallResponse(
            success=True,
            message="Git hook installed successfully",
            hook_path=result.get("hook_path"),
            chained=result.get("chained"),
            backup_created=result.get("backup_created"),
            installed_at=result.get("installed_at")
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to install git hook: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to install git hook: {str(e)}"
        )


@router.post(
    "/{project_id}/git-hook/uninstall",
    response_model=GitHookUninstallResponse,
    summary="Uninstall git hook from project",
    description="Remove the post-commit git hook from the project repository"
)
async def uninstall_git_hook(
    project_id: str,
    request: GitHookUninstallRequest,
    installer: GitHookInstaller = Depends(get_hook_installer),
    project_service: ProjectService = Depends(get_project_service)
) -> GitHookUninstallResponse:
    """
    Uninstall the post-commit git hook from the project repository.

    Args:
        project_id: UUID of the project
        request: Uninstallation configuration
        installer: GitHookInstaller dependency
        project_service: ProjectService dependency

    Returns:
        Uninstallation status and details

    Raises:
        HTTPException: If uninstallation fails
    """
    try:
        # Get project from database
        project = await project_service.get_project(project_id)

        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project not found: {project_id}"
            )

        # Check if project has local_path
        if not project.get("local_path"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Project does not have a local_path configured"
            )

        local_path = project["local_path"]

        # Uninstall the hook
        result = await installer.uninstall_hook(
            repo_path=local_path,
            hook_name="post-commit",
            restore_backup=request.restore_backup
        )

        logger.info(f"Uninstalled git hook for project {project_id}")

        return GitHookUninstallResponse(
            success=True,
            message="Git hook uninstalled successfully",
            hook_path=result.get("hook_path"),
            backup_restored=result.get("backup_restored"),
            uninstalled_at=result.get("uninstalled_at")
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to uninstall git hook: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to uninstall git hook: {str(e)}"
        )


@router.get(
    "/{project_id}/git-hook/status",
    response_model=GitHookStatusResponse,
    summary="Get git hook status",
    description="Check if git hook is installed and get its status"
)
async def get_git_hook_status(
    project_id: str,
    installer: GitHookInstaller = Depends(get_hook_installer),
    project_service: ProjectService = Depends(get_project_service)
) -> GitHookStatusResponse:
    """
    Get the status of the git hook for a project.

    Args:
        project_id: UUID of the project
        installer: GitHookInstaller dependency
        project_service: ProjectService dependency

    Returns:
        Hook status information

    Raises:
        HTTPException: If status check fails
    """
    try:
        # Get project from database
        project = await project_service.get_project(project_id)

        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project not found: {project_id}"
            )

        # Check if project has local_path
        if not project.get("local_path"):
            return GitHookStatusResponse(
                installed=False,
                hook_path=None,
                has_backup=None,
                is_archon_hook=None
            )

        local_path = project["local_path"]

        # Get hook status
        result = await installer.is_hook_installed(
            repo_path=local_path,
            hook_name="post-commit"
        )

        return GitHookStatusResponse(
            installed=result.get("installed", False),
            hook_path=result.get("hook_path"),
            has_backup=result.get("has_backup"),
            is_archon_hook=result.get("is_archon_hook"),
            size_bytes=result.get("size_bytes"),
            modified_at=result.get("modified_at")
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get git hook status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get git hook status: {str(e)}"
        )
