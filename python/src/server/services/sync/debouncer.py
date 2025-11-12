"""
Debouncer Service for batching and debouncing file change events.

This module provides debouncing to group rapid file changes and reduce
sync operations, improving performance and reducing database writes.
"""

import asyncio
import logging
from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class FileEvent:
    """Represents a file change event."""
    type: str  # created, modified, deleted
    project_id: str
    file_path: str
    timestamp: float


class DebouncerService:
    """
    Service for debouncing and batching file change events.

    Groups rapid file changes to minimize sync operations and prevent
    overwhelming the sync service with individual file events.
    """

    def __init__(
        self,
        debounce_seconds: float = 2.0,
        max_batch_size: int = 50,
        on_flush_callback: Optional[callable] = None
    ):
        """
        Initialize debouncer service.

        Args:
            debounce_seconds: Time to wait after last event before flushing
            max_batch_size: Maximum events before forcing immediate flush
            on_flush_callback: Optional callback when events are flushed
        """
        self.debounce_seconds = debounce_seconds
        self.max_batch_size = max_batch_size
        self.on_flush_callback = on_flush_callback

        # project_id -> file_path -> event (keeps latest event per file)
        self.pending_events: Dict[str, Dict[str, FileEvent]] = {}

        # project_id -> timer task
        self.timers: Dict[str, asyncio.Task] = {}

        logger.info(
            f"DebouncerService initialized: "
            f"debounce={debounce_seconds}s, max_batch={max_batch_size}"
        )

    async def add_event(self, event_data: dict) -> None:
        """
        Add event and start/reset debounce timer.

        Args:
            event_data: Dictionary with type, project_id, file_path, timestamp
        """
        try:
            # Create FileEvent from dict
            event = FileEvent(
                type=event_data["type"],
                project_id=event_data["project_id"],
                file_path=event_data["file_path"],
                timestamp=event_data["timestamp"]
            )

            project_id = event.project_id

            # Initialize project dict if needed
            if project_id not in self.pending_events:
                self.pending_events[project_id] = {}

            # Store event (overwrites previous event for same file)
            self.pending_events[project_id][event.file_path] = event

            logger.debug(
                f"Added {event.type} event for {event.file_path} "
                f"(project: {project_id})"
            )

            # Cancel existing timer
            if project_id in self.timers:
                self.timers[project_id].cancel()

            # Check if batch size exceeded
            batch_size = len(self.pending_events[project_id])
            if batch_size >= self.max_batch_size:
                logger.info(
                    f"Max batch size reached for project {project_id}, "
                    f"flushing immediately"
                )
                await self._flush_project(project_id)
            else:
                # Start new timer
                self.timers[project_id] = asyncio.create_task(
                    self._debounce_timer(project_id)
                )

        except KeyError as e:
            logger.error(f"Invalid event data, missing key: {e}")
        except Exception as e:
            logger.error(f"Error adding event: {e}")

    async def _debounce_timer(self, project_id: str) -> None:
        """
        Timer that triggers flush after debounce period.

        Args:
            project_id: Project to flush after timer expires
        """
        try:
            await asyncio.sleep(self.debounce_seconds)
            await self._flush_project(project_id)
        except asyncio.CancelledError:
            # Timer was cancelled, don't flush
            logger.debug(f"Debounce timer cancelled for project {project_id}")
        except Exception as e:
            logger.error(f"Error in debounce timer for project {project_id}: {e}")

    async def flush(self, project_id: str) -> List[FileEvent]:
        """
        Manually flush pending events for a project.

        Args:
            project_id: Project to flush events for

        Returns:
            List of flushed file events
        """
        return await self._flush_project(project_id)

    async def _flush_project(self, project_id: str) -> List[FileEvent]:
        """
        Flush all pending events for a project.

        Args:
            project_id: Project to flush

        Returns:
            List of flushed events
        """
        try:
            if project_id not in self.pending_events:
                return []

            # Get all events for project
            events_dict = self.pending_events.pop(project_id, {})

            # Cancel timer if exists
            if project_id in self.timers:
                self.timers[project_id].cancel()
                del self.timers[project_id]

            if not events_dict:
                return []

            # Convert to list and deduplicate
            events = list(events_dict.values())
            events = self._deduplicate_events(events)

            logger.info(
                f"Flushed {len(events)} events for project {project_id}"
            )

            # Trigger callback if provided
            if self.on_flush_callback:
                try:
                    await self.on_flush_callback(project_id, events)
                except Exception as e:
                    logger.error(f"Error in flush callback: {e}")

            return events

        except Exception as e:
            logger.error(f"Error flushing project {project_id}: {e}")
            return []

    def _deduplicate_events(self, events: List[FileEvent]) -> List[FileEvent]:
        """
        Remove duplicate events, keeping the latest event per file.

        Args:
            events: List of file events

        Returns:
            Deduplicated list of events
        """
        # Events are already deduplicated by file_path in the dict,
        # but this method handles edge cases and provides flexibility

        file_events: Dict[str, FileEvent] = {}

        for event in events:
            if event.file_path not in file_events:
                file_events[event.file_path] = event
            else:
                # Keep the latest event
                if event.timestamp > file_events[event.file_path].timestamp:
                    file_events[event.file_path] = event

        return list(file_events.values())

    async def flush_all(self) -> Dict[str, List[FileEvent]]:
        """
        Flush all pending events for all projects.

        Returns:
            Dictionary mapping project_id to list of flushed events
        """
        results = {}

        project_ids = list(self.pending_events.keys())
        for project_id in project_ids:
            events = await self._flush_project(project_id)
            if events:
                results[project_id] = events

        logger.info(f"Flushed all events for {len(results)} projects")
        return results

    def get_pending_count(self, project_id: Optional[str] = None) -> int:
        """
        Get count of pending events.

        Args:
            project_id: Optional project ID to filter by

        Returns:
            Count of pending events
        """
        if project_id:
            return len(self.pending_events.get(project_id, {}))
        else:
            return sum(len(events) for events in self.pending_events.values())

    async def cleanup(self) -> None:
        """
        Clean up all pending timers and flush remaining events.
        """
        logger.info("Cleaning up debouncer service")

        # Cancel all timers
        for timer in self.timers.values():
            timer.cancel()

        # Flush all pending events
        await self.flush_all()

        logger.info("Debouncer service cleanup complete")
