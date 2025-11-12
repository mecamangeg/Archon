"""
Health Monitor for sync worker.

Monitors worker health via heartbeat tracking and provides automatic
restart capabilities for failure recovery.
"""

import asyncio
import logging
import psutil
from typing import Optional
from datetime import datetime, timedelta

from src.server.services.sync.sync_worker import SyncWorker

logger = logging.getLogger(__name__)


class HealthMonitor:
    """
    Monitor health of sync worker and file watchers.

    Tracks heartbeat, detects failures, and provides automatic restart
    with failure tracking and alerting.
    """

    def __init__(
        self,
        worker: SyncWorker,
        heartbeat_timeout: int = 30,
        check_interval: int = 10,
        max_failures: int = 3
    ):
        """
        Initialize health monitor.

        Args:
            worker: SyncWorker instance to monitor
            heartbeat_timeout: Seconds before heartbeat considered stale
            check_interval: Seconds between health checks
            max_failures: Maximum restart attempts before alerting
        """
        self.worker = worker
        self.heartbeat_timeout = heartbeat_timeout
        self.check_interval = check_interval
        self.max_failures = max_failures

        self.last_heartbeat: Optional[datetime] = None
        self.failure_count = 0
        self.running = False
        self.restart_count = 0

        logger.info(
            f"HealthMonitor initialized: timeout={heartbeat_timeout}s, "
            f"interval={check_interval}s, max_failures={max_failures}"
        )

    async def monitor_loop(self) -> None:
        """
        Continuous health monitoring loop.

        Checks worker health at regular intervals and triggers restart
        if unhealthy.
        """
        logger.info("Starting health monitoring loop")
        self.running = True

        while self.running:
            try:
                # Check health
                is_healthy = await self.check_health()

                if not is_healthy:
                    logger.warning("Worker unhealthy, attempting restart")

                    # Attempt restart
                    restart_success = await self.restart_worker()

                    if restart_success:
                        self.failure_count = 0
                        logger.info("Worker restarted successfully")
                    else:
                        self.failure_count += 1
                        logger.error(
                            f"Worker restart failed "
                            f"(attempt {self.failure_count}/{self.max_failures})"
                        )

                        # Alert if max failures reached
                        if self.failure_count >= self.max_failures:
                            await self._alert_max_failures()

                # Wait before next check
                await asyncio.sleep(self.check_interval)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in health monitoring loop: {e}")
                await asyncio.sleep(self.check_interval)

    async def check_health(self) -> bool:
        """
        Check if worker is healthy.

        Returns:
            True if worker is healthy, False otherwise
        """
        try:
            # Check if worker is running
            if not self.worker.running:
                logger.warning("Worker not running")
                return False

            # Check heartbeat
            last_heartbeat = self.worker.last_heartbeat

            if not last_heartbeat:
                logger.warning("No heartbeat recorded")
                return False

            # Check heartbeat freshness
            now = datetime.now()
            time_since_heartbeat = (now - last_heartbeat).total_seconds()

            if time_since_heartbeat > self.heartbeat_timeout:
                logger.warning(
                    f"Heartbeat stale: {time_since_heartbeat:.1f}s since last beat"
                )
                return False

            # Update last seen heartbeat
            self.last_heartbeat = last_heartbeat

            logger.debug("Worker health check passed")
            return True

        except Exception as e:
            logger.error(f"Error checking worker health: {e}")
            return False

    async def restart_worker(self) -> bool:
        """
        Restart the worker.

        Returns:
            True if restart successful, False otherwise
        """
        try:
            logger.info("Restarting sync worker")

            # Stop worker
            await self.worker.stop()

            # Wait briefly for cleanup
            await asyncio.sleep(2)

            # Start worker
            await self.worker.start()

            # Wait for heartbeat
            await asyncio.sleep(5)

            # Verify healthy
            is_healthy = await self.check_health()

            if is_healthy:
                self.restart_count += 1
                logger.info(f"Worker restart successful (restart #{self.restart_count})")
                return True
            else:
                logger.error("Worker restart failed health check")
                return False

        except Exception as e:
            logger.error(f"Error restarting worker: {e}")
            return False

    async def get_metrics(self) -> dict:
        """
        Get performance and health metrics.

        Returns:
            Dictionary with metrics
        """
        try:
            # Get process info
            process = psutil.Process()

            # CPU and memory
            cpu_percent = process.cpu_percent(interval=1)
            memory_info = process.memory_info()
            memory_mb = memory_info.rss / 1024 / 1024

            # Worker status
            worker_status = self.worker.get_status()

            # Health info
            time_since_heartbeat = None
            if self.worker.last_heartbeat:
                time_since_heartbeat = (
                    datetime.now() - self.worker.last_heartbeat
                ).total_seconds()

            return {
                "healthy": await self.check_health(),
                "running": self.worker.running,
                "restart_count": self.restart_count,
                "failure_count": self.failure_count,
                "cpu_percent": cpu_percent,
                "memory_mb": round(memory_mb, 2),
                "watched_projects": worker_status["watched_projects"],
                "pending_events": worker_status["pending_events"],
                "time_since_heartbeat": round(time_since_heartbeat, 1) if time_since_heartbeat else None,
                "last_heartbeat": worker_status["last_heartbeat"]
            }

        except Exception as e:
            logger.error(f"Error getting metrics: {e}")
            return {
                "healthy": False,
                "error": str(e)
            }

    async def _alert_max_failures(self) -> None:
        """
        Alert on maximum restart failures.

        This method can be extended to send notifications via email,
        Slack, PagerDuty, etc.
        """
        logger.critical(
            f"ALERT: Maximum restart failures reached ({self.max_failures}). "
            f"Manual intervention required."
        )

        # TODO: Integrate with alerting system
        # - Send email notification
        # - Post to Slack channel
        # - Create PagerDuty incident
        # - Update monitoring dashboard

    async def stop(self) -> None:
        """Stop the health monitoring loop."""
        logger.info("Stopping health monitor")
        self.running = False

    def get_status(self) -> dict:
        """
        Get current monitor status.

        Returns:
            Status dictionary
        """
        return {
            "running": self.running,
            "restart_count": self.restart_count,
            "failure_count": self.failure_count,
            "max_failures": self.max_failures,
            "last_heartbeat": self.last_heartbeat.isoformat() if self.last_heartbeat else None
        }
