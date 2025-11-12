"""
Sync Worker for background automatic synchronization.

This module provides the background worker that manages file watchers,
processes debounced events, and triggers incremental syncs automatically.
"""

import asyncio
import logging
from typing import Optional, List, Set
from datetime import datetime, timedelta
from supabase import Client as SupabaseClient

from src.server.services.sync.incremental_sync_service import IncrementalSyncService
from src.server.services.sync.file_watcher import FileWatcherService
from src.server.services.sync.debouncer import DebouncerService, FileEvent

logger = logging.getLogger(__name__)


class SyncWorker:
    """
    Background worker for automatic project synchronization.

    Manages file watchers, processes events, and triggers incremental
    syncs for projects with auto-sync enabled.
    """

    def __init__(
        self,
        db: SupabaseClient,
        sync_service: IncrementalSyncService,
        file_watcher: FileWatcherService,
        debouncer: DebouncerService,
        poll_interval: int = 60,
        periodic_sync_interval: int = 3600
    ):
        """
        Initialize sync worker.

        Args:
            db: Supabase database client
            sync_service: Incremental sync service
            file_watcher: File watcher service
            debouncer: Debouncer service
            poll_interval: Seconds between project discovery polls
            periodic_sync_interval: Seconds between periodic syncs
        """
        self.db = db
        self.sync_service = sync_service
        self.file_watcher = file_watcher
        self.debouncer = debouncer
        self.poll_interval = poll_interval
        self.periodic_sync_interval = periodic_sync_interval

        self.running = False
        self.event_queue = file_watcher.event_queue
        self.watched_projects: Set[str] = set()
        self.last_heartbeat: Optional[datetime] = None

        # Task references
        self.tasks: List[asyncio.Task] = []

        logger.info(
            f"SyncWorker initialized: poll={poll_interval}s, "
            f"periodic={periodic_sync_interval}s"
        )

    async def start(self) -> None:
        """Start the background worker and all monitoring loops."""
        if self.running:
            logger.warning("SyncWorker already running")
            return

        self.running = True
        logger.info("Starting SyncWorker")

        # Set up flush callback for debouncer
        self.debouncer.on_flush_callback = self._handle_flushed_events

        # Start monitoring loops
        self.tasks = [
            asyncio.create_task(self._poll_projects_loop()),
            asyncio.create_task(self._process_events_loop()),
            asyncio.create_task(self._periodic_sync_loop()),
            asyncio.create_task(self._heartbeat_loop())
        ]

        logger.info("SyncWorker started successfully")

    async def stop(self) -> None:
        """Stop the background worker gracefully."""
        if not self.running:
            logger.warning("SyncWorker not running")
            return

        logger.info("Stopping SyncWorker")
        self.running = False

        # Cancel all tasks
        for task in self.tasks:
            task.cancel()

        # Wait for tasks to complete
        await asyncio.gather(*self.tasks, return_exceptions=True)

        # Clean up services
        await self.file_watcher.cleanup()
        await self.debouncer.cleanup()

        logger.info("SyncWorker stopped successfully")

    async def _poll_projects_loop(self) -> None:
        """Periodically poll for new auto-sync projects."""
        logger.info("Starting project polling loop")

        while self.running:
            try:
                await self._discover_auto_sync_projects()
                await asyncio.sleep(self.poll_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in project polling loop: {e}")
                await asyncio.sleep(self.poll_interval)

    async def _process_events_loop(self) -> None:
        """Process file change events from the queue."""
        logger.info("Starting event processing loop")

        while self.running:
            try:
                # Get event from queue (with timeout to allow shutdown)
                try:
                    event = await asyncio.wait_for(
                        self.event_queue.get(),
                        timeout=1.0
                    )

                    # Add to debouncer
                    await self.debouncer.add_event(event)

                except asyncio.TimeoutError:
                    # No events, continue loop
                    continue

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error processing event: {e}")

    async def _periodic_sync_loop(self) -> None:
        """Handle periodic sync mode projects."""
        logger.info("Starting periodic sync loop")

        while self.running:
            try:
                await self._trigger_periodic_syncs()
                await asyncio.sleep(self.periodic_sync_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in periodic sync loop: {e}")
                await asyncio.sleep(self.periodic_sync_interval)

    async def _heartbeat_loop(self) -> None:
        """Update heartbeat timestamp for health monitoring."""
        while self.running:
            try:
                self.last_heartbeat = datetime.now()
                await asyncio.sleep(10)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in heartbeat loop: {e}")
                await asyncio.sleep(10)

    async def _discover_auto_sync_projects(self) -> None:
        """Discover projects with auto-sync enabled and start watchers."""
        try:
            # Query projects with auto_sync_enabled = true
            response = self.db.table("projects").select(
                "id, local_path, sync_mode, auto_sync_enabled"
            ).eq("auto_sync_enabled", True).execute()

            if not response.data:
                return

            current_project_ids = {p["id"] for p in response.data}

            # Start watchers for new projects
            for project in response.data:
                project_id = project["id"]
                local_path = project["local_path"]
                sync_mode = project.get("sync_mode", "manual")

                # Only start watcher for real-time mode
                if sync_mode == "realtime" and project_id not in self.watched_projects:
                    success = await self.file_watcher.start_watching(
                        project_id, local_path
                    )

                    if success:
                        self.watched_projects.add(project_id)
                        logger.info(f"Started watching project {project_id}")

            # Stop watchers for removed projects
            removed_projects = self.watched_projects - current_project_ids
            for project_id in removed_projects:
                await self.file_watcher.stop_watching(project_id)
                self.watched_projects.discard(project_id)
                logger.info(f"Stopped watching project {project_id}")

        except Exception as e:
            logger.error(f"Error discovering auto-sync projects: {e}")

    async def _handle_flushed_events(
        self,
        project_id: str,
        events: List[FileEvent]
    ) -> None:
        """
        Handle flushed events from debouncer by triggering sync.

        Args:
            project_id: Project ID
            events: List of file events to process
        """
        try:
            if not events:
                return

            logger.info(
                f"Handling {len(events)} flushed events for project {project_id}"
            )

            # Extract file paths
            changed_files = [event.file_path for event in events]

            # Trigger incremental sync
            stats = await self.sync_service.sync_project(
                project_id=project_id,
                changed_files=changed_files,
                trigger="auto"
            )

            logger.info(
                f"Auto-sync completed for project {project_id}: "
                f"{stats.get('files_processed', 0)} files processed"
            )

        except Exception as e:
            logger.error(
                f"Error handling flushed events for project {project_id}: {e}"
            )

    async def _trigger_periodic_syncs(self) -> None:
        """Trigger syncs for projects in periodic mode."""
        try:
            # Query projects with periodic sync mode
            response = self.db.table("projects").select(
                "id, local_path, last_auto_sync"
            ).eq("auto_sync_enabled", True).eq("sync_mode", "periodic").execute()

            if not response.data:
                return

            now = datetime.now()

            for project in response.data:
                project_id = project["id"]
                last_sync_str = project.get("last_auto_sync")

                # Check if sync is due
                should_sync = True
                if last_sync_str:
                    last_sync = datetime.fromisoformat(last_sync_str.replace('Z', '+00:00'))
                    time_since_sync = (now - last_sync).total_seconds()
                    should_sync = time_since_sync >= self.periodic_sync_interval

                if should_sync:
                    logger.info(f"Triggering periodic sync for project {project_id}")

                    try:
                        stats = await self.sync_service.sync_project(
                            project_id=project_id,
                            trigger="periodic"
                        )

                        logger.info(
                            f"Periodic sync completed for project {project_id}: "
                            f"{stats.get('files_processed', 0)} files processed"
                        )
                    except Exception as e:
                        logger.error(
                            f"Error in periodic sync for project {project_id}: {e}"
                        )

        except Exception as e:
            logger.error(f"Error triggering periodic syncs: {e}")

    def get_status(self) -> dict:
        """
        Get current worker status.

        Returns:
            Dictionary with worker status information
        """
        return {
            "running": self.running,
            "watched_projects": len(self.watched_projects),
            "pending_events": self.debouncer.get_pending_count(),
            "last_heartbeat": self.last_heartbeat.isoformat() if self.last_heartbeat else None
        }

    def is_healthy(self) -> bool:
        """
        Check if worker is healthy.

        Returns:
            True if worker is running and heartbeat is recent
        """
        if not self.running:
            return False

        if not self.last_heartbeat:
            return False

        # Check heartbeat within last 30 seconds
        time_since_heartbeat = (datetime.now() - self.last_heartbeat).total_seconds()
        return time_since_heartbeat < 30
