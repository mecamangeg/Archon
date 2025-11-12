"""
File Watcher Service for monitoring project directories.

This module provides cross-platform file system monitoring using the watchdog library.
It detects create, modify, and delete events with smart exclusions for common ignored
directories and files.
"""

import asyncio
import logging
from pathlib import Path
from typing import Dict, Optional
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileSystemEvent

from src.server.services.sync.incremental_sync_service import IncrementalSyncService

logger = logging.getLogger(__name__)


class CodebaseEventHandler(FileSystemEventHandler):
    """
    Handler for file system events with smart exclusions.

    Filters out common development artifacts and emits events for
    meaningful file changes.
    """

    EXCLUDED_PATTERNS = [
        '*/node_modules/*', '*/__pycache__/*', '*/.git/*',
        '*/dist/*', '*/build/*', '*/.next/*', '*/.nuxt/*',
        '*/venv/*', '*/env/*', '*/.venv/*', '*/.pytest_cache/*',
        '*/coverage/*', '*/.coverage/*', '*/.mypy_cache/*',
        '*.pyc', '*.pyo', '*.swp', '*.DS_Store', '*.log',
        '*/.idea/*', '*/.vscode/*', '*.tmp', '*.temp'
    ]

    def __init__(self, project_id: str, event_queue: asyncio.Queue):
        """
        Initialize event handler.

        Args:
            project_id: Unique identifier for the project being monitored
            event_queue: Asyncio queue for thread-safe event communication
        """
        super().__init__()
        self.project_id = project_id
        self.event_queue = event_queue
        logger.info(f"Initialized event handler for project {project_id}")

    def on_created(self, event: FileSystemEvent) -> None:
        """
        Handle file creation events.

        Args:
            event: File system event from watchdog
        """
        if event.is_directory:
            return

        if self._should_ignore(event.src_path):
            return

        self._emit_event("created", event.src_path)

    def on_modified(self, event: FileSystemEvent) -> None:
        """
        Handle file modification events.

        Args:
            event: File system event from watchdog
        """
        if event.is_directory:
            return

        if self._should_ignore(event.src_path):
            return

        self._emit_event("modified", event.src_path)

    def on_deleted(self, event: FileSystemEvent) -> None:
        """
        Handle file deletion events.

        Args:
            event: File system event from watchdog
        """
        if event.is_directory:
            return

        if self._should_ignore(event.src_path):
            return

        self._emit_event("deleted", event.src_path)

    def _should_ignore(self, path: str) -> bool:
        """
        Check if path matches exclusion patterns.

        Args:
            path: File path to check

        Returns:
            True if path should be ignored, False otherwise
        """
        path_obj = Path(path)

        for pattern in self.EXCLUDED_PATTERNS:
            if pattern.startswith('*.'):
                # File extension pattern
                if path_obj.suffix == pattern[1:]:
                    return True
            elif pattern.startswith('*/') and pattern.endswith('/*'):
                # Directory pattern
                dir_name = pattern[2:-2]
                if dir_name in path_obj.parts:
                    return True

        return False

    def _emit_event(self, event_type: str, file_path: str) -> None:
        """
        Emit file change event to queue.

        Args:
            event_type: Type of event (created, modified, deleted)
            file_path: Path to the file
        """
        import time

        event_data = {
            "type": event_type,
            "project_id": self.project_id,
            "file_path": file_path,
            "timestamp": time.time()
        }

        # Put event in queue (non-blocking from sync thread)
        try:
            self.event_queue.put_nowait(event_data)
            logger.debug(f"Emitted {event_type} event for {file_path}")
        except asyncio.QueueFull:
            logger.warning(f"Event queue full, dropping event for {file_path}")


class FileWatcherService:
    """
    Service for monitoring file system changes in project directories.

    Manages watchdog observers for multiple projects and provides
    lifecycle management for file watching.
    """

    def __init__(self, sync_service: Optional[IncrementalSyncService] = None):
        """
        Initialize file watcher service.

        Args:
            sync_service: Optional incremental sync service for triggering syncs
        """
        self.sync_service = sync_service
        self.observers: Dict[str, Observer] = {}
        self.event_handlers: Dict[str, CodebaseEventHandler] = {}
        self.event_queue: asyncio.Queue = asyncio.Queue()
        logger.info("FileWatcherService initialized")

    async def start_watching(self, project_id: str, local_path: str) -> bool:
        """
        Start watching a project directory.

        Args:
            project_id: Unique identifier for the project
            local_path: Local file system path to monitor

        Returns:
            True if watcher started successfully, False otherwise
        """
        try:
            # Check if already watching
            if project_id in self.observers:
                logger.warning(f"Already watching project {project_id}")
                return True

            # Validate path exists
            path_obj = Path(local_path)
            if not path_obj.exists():
                logger.error(f"Path does not exist: {local_path}")
                return False

            if not path_obj.is_dir():
                logger.error(f"Path is not a directory: {local_path}")
                return False

            # Create event handler
            event_handler = CodebaseEventHandler(project_id, self.event_queue)

            # Create and start observer
            observer = Observer()
            observer.schedule(event_handler, str(path_obj), recursive=True)
            observer.start()

            # Store references
            self.observers[project_id] = observer
            self.event_handlers[project_id] = event_handler

            logger.info(f"Started watching project {project_id} at {local_path}")
            return True

        except PermissionError as e:
            logger.error(f"Permission denied watching {local_path}: {e}")
            return False
        except Exception as e:
            logger.error(f"Error starting watcher for project {project_id}: {e}")
            return False

    async def stop_watching(self, project_id: str) -> bool:
        """
        Stop watching a project directory.

        Args:
            project_id: Unique identifier for the project

        Returns:
            True if watcher stopped successfully, False otherwise
        """
        try:
            if project_id not in self.observers:
                logger.warning(f"Not watching project {project_id}")
                return False

            # Stop and join observer
            observer = self.observers[project_id]
            observer.stop()
            observer.join(timeout=5.0)

            # Clean up references
            del self.observers[project_id]
            del self.event_handlers[project_id]

            logger.info(f"Stopped watching project {project_id}")
            return True

        except Exception as e:
            logger.error(f"Error stopping watcher for project {project_id}: {e}")
            return False

    def is_watching(self, project_id: str) -> bool:
        """
        Check if project is being watched.

        Args:
            project_id: Unique identifier for the project

        Returns:
            True if project is being watched, False otherwise
        """
        is_active = project_id in self.observers and self.observers[project_id].is_alive()
        return is_active

    async def add_project(self, project_id: str, local_path: str) -> bool:
        """
        Add a project to the watch list.

        Alias for start_watching for consistency with remove_project.

        Args:
            project_id: Unique identifier for the project
            local_path: Local file system path to monitor

        Returns:
            True if project added successfully, False otherwise
        """
        return await self.start_watching(project_id, local_path)

    async def remove_project(self, project_id: str) -> bool:
        """
        Remove a project from the watch list.

        Alias for stop_watching for consistency with add_project.

        Args:
            project_id: Unique identifier for the project

        Returns:
            True if project removed successfully, False otherwise
        """
        return await self.stop_watching(project_id)

    async def get_watched_projects(self) -> list[str]:
        """
        Get list of currently watched project IDs.

        Returns:
            List of project IDs currently being watched
        """
        return list(self.observers.keys())

    async def cleanup(self) -> None:
        """
        Clean up all observers and resources.

        Should be called on shutdown to ensure proper cleanup.
        """
        logger.info("Cleaning up file watcher service")

        project_ids = list(self.observers.keys())
        for project_id in project_ids:
            await self.stop_watching(project_id)

        logger.info("File watcher service cleanup complete")
