"""
Standalone worker process for background synchronization.

This script runs the sync worker as a separate process with proper
signal handling and lifecycle management.
"""

import asyncio
import logging
import signal
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from src.server.config.database import get_db_client
from src.server.services.sync.incremental_sync_service import IncrementalSyncService
from src.server.services.sync.file_watcher import FileWatcherService
from src.server.services.sync.debouncer import DebouncerService
from src.server.services.sync.sync_worker import SyncWorker

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('sync_worker.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)


class WorkerManager:
    """Manager for the sync worker process."""

    def __init__(self):
        """Initialize worker manager."""
        self.worker: Optional[SyncWorker] = None
        self.shutdown_event = asyncio.Event()

    def setup_signal_handlers(self) -> None:
        """Set up signal handlers for graceful shutdown."""
        for sig in (signal.SIGINT, signal.SIGTERM):
            signal.signal(sig, self._signal_handler)

        logger.info("Signal handlers registered")

    def _signal_handler(self, signum, frame) -> None:
        """
        Handle shutdown signals.

        Args:
            signum: Signal number
            frame: Current stack frame
        """
        sig_name = signal.Signals(signum).name
        logger.info(f"Received signal {sig_name}, initiating shutdown")
        self.shutdown_event.set()

    async def run(self) -> None:
        """Run the worker process."""
        logger.info("Starting sync worker process")

        try:
            # Initialize database
            logger.info("Initializing database connection")
            db = get_db_client()

            # Initialize services
            logger.info("Initializing services")
            sync_service = IncrementalSyncService(db)
            file_watcher = FileWatcherService(sync_service)
            debouncer = DebouncerService(
                debounce_seconds=2.0,
                max_batch_size=50
            )

            # Create worker
            self.worker = SyncWorker(
                db=db,
                sync_service=sync_service,
                file_watcher=file_watcher,
                debouncer=debouncer,
                poll_interval=60,
                periodic_sync_interval=3600
            )

            # Start worker
            await self.worker.start()
            logger.info("Sync worker started successfully")

            # Wait for shutdown signal
            await self.shutdown_event.wait()

            # Graceful shutdown
            logger.info("Initiating graceful shutdown")
            await self.worker.stop()
            logger.info("Sync worker stopped successfully")

        except KeyboardInterrupt:
            logger.info("Received keyboard interrupt")
        except Exception as e:
            logger.error(f"Fatal error in worker process: {e}", exc_info=True)
            sys.exit(1)
        finally:
            logger.info("Sync worker process terminated")


def main() -> None:
    """Main entry point for worker process."""
    manager = WorkerManager()
    manager.setup_signal_handlers()

    # Run event loop
    try:
        asyncio.run(manager.run())
    except KeyboardInterrupt:
        logger.info("Process interrupted by user")
    except Exception as e:
        logger.error(f"Unhandled exception: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
