"""
Project Service Sync Extensions
Phase 1, Task 1.2
Adds sync configuration methods to ProjectService
"""

from typing import Optional, Dict, List
from datetime import datetime
import os
import logging

logger = logging.getLogger(__name__)


class ProjectServiceSyncMixin:
    """
    Mixin for ProjectService to add sync-related methods.

    This can be mixed into the existing ProjectService class or used as a reference
    for adding these methods directly to ProjectService.
    """

    async def update_project_sync_config(
        self,
        project_id: str,
        local_path: Optional[str] = None,
        sync_mode: Optional[str] = None,
        auto_sync_enabled: Optional[bool] = None
    ) -> Dict:
        """
        Update sync configuration for a project.

        Args:
            project_id: Project UUID
            local_path: Absolute path to project directory
            sync_mode: 'manual', 'realtime', 'periodic', or 'git-hook'
            auto_sync_enabled: Enable/disable automatic sync

        Returns:
            Updated project data

        Raises:
            ValueError: If local_path is invalid
        """
        # Validate local path if provided
        if local_path is not None:
            self._validate_local_path(local_path)

        # Build update dict
        update_data = {}
        if local_path is not None:
            update_data['local_path'] = local_path
        if sync_mode is not None:
            update_data['sync_mode'] = sync_mode
        if auto_sync_enabled is not None:
            update_data['auto_sync_enabled'] = auto_sync_enabled

        update_data['updated_at'] = datetime.now().isoformat()

        # Update database
        result = await self.db.table('projects')\
            .update(update_data)\
            .eq('id', project_id)\
            .execute()

        if not result.data:
            raise ValueError(f"Project not found: {project_id}")

        logger.info(f"Updated sync config for project {project_id}: {update_data}")
        return result.data[0]

    def _validate_local_path(self, path: str) -> None:
        """
        Validate that local path is safe and accessible.

        Raises:
            ValueError: If path is invalid or inaccessible
        """
        # Resolve to absolute path
        resolved = os.path.abspath(os.path.expanduser(path))

        # Deny system directories (security)
        forbidden_prefixes = [
            '/etc', '/usr', '/bin', '/sbin', '/sys', '/proc',
            'C:\\Windows', 'C:\\Program Files', '/var/lib', '/root',
            'C:\\Windows\\System32', '/System', '/Library/System'
        ]

        for forbidden in forbidden_prefixes:
            if resolved.startswith(forbidden):
                raise ValueError(
                    f"Cannot access system directory: {resolved}. "
                    "Please link to a user project directory."
                )

        # Check existence
        if not os.path.exists(resolved):
            raise ValueError(f"Path does not exist: {resolved}")

        # Check read permission
        if not os.access(resolved, os.R_OK):
            raise ValueError(f"No read permission for path: {resolved}")

        # Check if it's a directory
        if not os.path.isdir(resolved):
            raise ValueError(f"Path is not a directory: {resolved}")

    async def get_projects_with_auto_sync(self) -> List[Dict]:
        """
        Get all projects with auto-sync enabled.

        Returns:
            List of project data with local_path configured
        """
        result = await self.db.table('projects')\
            .select('*')\
            .eq('auto_sync_enabled', True)\
            .not_.is_('local_path', 'null')\
            .execute()

        return result.data if result.data else []

    async def update_project_sync_status(
        self,
        project_id: str,
        status: str,
        last_sync_at: Optional[datetime] = None,
        error_message: Optional[str] = None
    ) -> None:
        """
        Update sync status after sync operation.

        Args:
            project_id: Project UUID
            status: 'synced', 'syncing', 'error', or 'never_synced'
            last_sync_at: Timestamp of sync completion
            error_message: Error details if status is 'error'
        """
        update_data = {
            'sync_status': status,
            'updated_at': datetime.now().isoformat()
        }

        if last_sync_at:
            update_data['last_sync_at'] = last_sync_at.isoformat()

        if error_message:
            update_data['last_sync_error'] = error_message
        elif status == 'synced':
            # Clear error on successful sync
            update_data['last_sync_error'] = None

        await self.db.table('projects')\
            .update(update_data)\
            .eq('id', project_id)\
            .execute()

        logger.info(f"Updated sync status for project {project_id}: {status}")

    async def get_project_by_path(self, file_path: str) -> Optional[Dict]:
        """
        Find project by file path (for file watcher).

        Args:
            file_path: Absolute path to a file

        Returns:
            Project data if found, None otherwise
        """
        # Get all projects with local paths
        result = await self.db.table('projects')\
            .select('*')\
            .not_.is_('local_path', 'null')\
            .execute()

        if not result.data:
            return None

        # Check if file_path is within any project's local_path
        for project in result.data:
            project_path = project.get('local_path')
            if project_path and file_path.startswith(project_path):
                return project

        return None
