"""
Sync Queue for managing concurrent sync operations.

This module provides queue management to prevent concurrent syncs for
the same project and enforce resource limits.
"""

import asyncio
import logging
from typing import Dict, Optional, List, Set
from dataclasses import dataclass
from datetime import datetime
from enum import IntEnum

logger = logging.getLogger(__name__)


class SyncPriority(IntEnum):
    """Priority levels for sync operations (lower value = higher priority)."""
    MANUAL = 0  # User-initiated sync
    AUTO = 1    # Auto-sync from file watcher


@dataclass
class SyncOperation:
    """Represents a sync operation in the queue."""
    project_id: str
    changed_files: Optional[List[str]]
    priority: SyncPriority
    enqueued_at: datetime
    operation_id: str


class SyncQueue:
    """
    Queue manager for sync operations.

    Prevents concurrent syncs for the same project and enforces
    global concurrency limits.
    """

    def __init__(self, max_concurrent: int = 3):
        """
        Initialize sync queue.

        Args:
            max_concurrent: Maximum number of concurrent sync operations
        """
        self.max_concurrent = max_concurrent
        self.semaphore = asyncio.Semaphore(max_concurrent)

        # project_id -> priority queue
        self.queues: Dict[str, asyncio.PriorityQueue] = {}

        # project_ids currently syncing
        self.active_syncs: Set[str] = set()

        # operation_id -> SyncOperation (for tracking)
        self.operations: Dict[str, SyncOperation] = {}

        # Counter for operation IDs
        self._operation_counter = 0

        logger.info(f"SyncQueue initialized with max_concurrent={max_concurrent}")

    async def enqueue(
        self,
        project_id: str,
        changed_files: Optional[List[str]] = None,
        priority: int = 1
    ) -> str:
        """
        Add sync operation to queue.

        Args:
            project_id: Project to sync
            changed_files: Optional list of changed files for incremental sync
            priority: Priority level (0 = manual, 1 = auto)

        Returns:
            Operation ID for tracking
        """
        # Generate operation ID
        self._operation_counter += 1
        operation_id = f"sync_{project_id}_{self._operation_counter}"

        # Create operation
        operation = SyncOperation(
            project_id=project_id,
            changed_files=changed_files,
            priority=SyncPriority(priority),
            enqueued_at=datetime.now(),
            operation_id=operation_id
        )

        # Create queue for project if needed
        if project_id not in self.queues:
            self.queues[project_id] = asyncio.PriorityQueue()

        # Add to queue (priority, operation)
        await self.queues[project_id].put((operation.priority, operation))
        self.operations[operation_id] = operation

        logger.info(
            f"Enqueued sync operation {operation_id} for project {project_id} "
            f"with priority {operation.priority.name}"
        )

        return operation_id

    async def execute_next(
        self,
        project_id: str,
        sync_func: callable
    ) -> Optional[dict]:
        """
        Execute next sync operation for a project.

        Args:
            project_id: Project to sync
            sync_func: Async function to execute sync (returns stats dict)

        Returns:
            Sync statistics dict or None if no operation queued
        """
        # Check if queue exists and has items
        if project_id not in self.queues:
            return None

        if self.queues[project_id].empty():
            return None

        # Check if project already syncing
        if project_id in self.active_syncs:
            logger.debug(f"Project {project_id} already syncing, skipping")
            return None

        try:
            # Acquire semaphore (enforce global concurrency limit)
            async with self.semaphore:
                # Get next operation
                priority, operation = await self.queues[project_id].get()

                # Mark as active
                self.active_syncs.add(project_id)

                logger.info(
                    f"Executing sync operation {operation.operation_id} "
                    f"for project {project_id}"
                )

                try:
                    # Execute sync
                    stats = await sync_func(
                        project_id=project_id,
                        changed_files=operation.changed_files
                    )

                    logger.info(
                        f"Completed sync operation {operation.operation_id}: "
                        f"{stats.get('files_processed', 0)} files processed"
                    )

                    return stats

                except Exception as e:
                    logger.error(
                        f"Error executing sync operation {operation.operation_id}: {e}"
                    )
                    raise

                finally:
                    # Mark as inactive
                    self.active_syncs.discard(project_id)

                    # Clean up operation
                    self.operations.pop(operation.operation_id, None)

        except Exception as e:
            logger.error(f"Error in execute_next for project {project_id}: {e}")
            return None

    def get_status(self, project_id: Optional[str] = None) -> dict:
        """
        Get queue status.

        Args:
            project_id: Optional project ID to filter by

        Returns:
            Status dictionary
        """
        if project_id:
            queue = self.queues.get(project_id)
            return {
                "project_id": project_id,
                "queued": queue.qsize() if queue else 0,
                "active": project_id in self.active_syncs
            }
        else:
            total_queued = sum(q.qsize() for q in self.queues.values())
            return {
                "total_queued": total_queued,
                "active_syncs": len(self.active_syncs),
                "max_concurrent": self.max_concurrent,
                "available_slots": self.max_concurrent - len(self.active_syncs)
            }

    async def cancel(self, operation_id: str) -> bool:
        """
        Cancel a queued sync operation.

        Note: Cannot cancel operations that are already executing.

        Args:
            operation_id: Operation to cancel

        Returns:
            True if cancelled, False if not found or already executing
        """
        operation = self.operations.get(operation_id)
        if not operation:
            logger.warning(f"Operation {operation_id} not found")
            return False

        project_id = operation.project_id

        # Cannot cancel if already executing
        if project_id in self.active_syncs:
            logger.warning(
                f"Cannot cancel operation {operation_id}, already executing"
            )
            return False

        # Remove from tracking
        self.operations.pop(operation_id, None)

        logger.info(f"Cancelled sync operation {operation_id}")
        return True

    def is_active(self, project_id: str) -> bool:
        """
        Check if project is currently syncing.

        Args:
            project_id: Project to check

        Returns:
            True if project is actively syncing
        """
        return project_id in self.active_syncs

    def get_queue_size(self, project_id: str) -> int:
        """
        Get number of queued operations for a project.

        Args:
            project_id: Project to check

        Returns:
            Number of queued operations
        """
        queue = self.queues.get(project_id)
        return queue.qsize() if queue else 0

    async def cleanup(self) -> None:
        """Clean up queue resources."""
        logger.info("Cleaning up sync queue")

        # Wait for active syncs to complete (with timeout)
        max_wait = 30  # seconds
        waited = 0

        while self.active_syncs and waited < max_wait:
            await asyncio.sleep(1)
            waited += 1

        if self.active_syncs:
            logger.warning(
                f"Sync queue cleanup: {len(self.active_syncs)} active syncs "
                f"still running after {max_wait}s"
            )

        logger.info("Sync queue cleanup complete")
