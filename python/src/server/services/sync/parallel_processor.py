"""
Parallel file processing with asyncio for improved sync performance.

Provides:
- Concurrent file processing with configurable workers
- Progress tracking for large operations
- Semaphore-based concurrency control
- Error isolation (one file failure doesn't stop others)
"""

import asyncio
from typing import List, Callable, Any, Optional, Dict
from dataclasses import dataclass
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


@dataclass
class ProcessingProgress:
    """Track processing progress"""
    total_files: int
    processed_files: int
    failed_files: int
    current_file: Optional[str] = None
    start_time: Optional[datetime] = None

    @property
    def percent_complete(self) -> float:
        """Calculate completion percentage"""
        if self.total_files == 0:
            return 0.0
        return (self.processed_files / self.total_files) * 100

    @property
    def success_rate(self) -> float:
        """Calculate success rate"""
        if self.processed_files == 0:
            return 0.0
        successful = self.processed_files - self.failed_files
        return (successful / self.processed_files) * 100

    @property
    def elapsed_seconds(self) -> float:
        """Calculate elapsed time in seconds"""
        if not self.start_time:
            return 0.0
        return (datetime.now() - self.start_time).total_seconds()

    @property
    def files_per_second(self) -> float:
        """Calculate processing rate"""
        elapsed = self.elapsed_seconds
        if elapsed == 0:
            return 0.0
        return self.processed_files / elapsed

    @property
    def estimated_seconds_remaining(self) -> float:
        """Estimate remaining time"""
        rate = self.files_per_second
        if rate == 0:
            return 0.0
        remaining_files = self.total_files - self.processed_files
        return remaining_files / rate


@dataclass
class ProcessingResult:
    """Result from processing a single file"""
    file_path: str
    success: bool
    result: Any = None
    error: Optional[Exception] = None
    duration_seconds: float = 0.0


class ParallelFileProcessor:
    """
    Process files in parallel with configurable concurrency.

    Example:
        processor = ParallelFileProcessor(max_workers=5)

        async def process_file(file_path):
            # Process single file
            return result

        results = await processor.process_files(
            file_paths=['file1.py', 'file2.py', ...],
            process_func=process_file
        )
    """

    def __init__(
        self,
        max_workers: int = 5,
        progress_callback: Optional[Callable[[ProcessingProgress], None]] = None
    ):
        """
        Initialize parallel processor.

        Args:
            max_workers: Maximum concurrent file processing tasks
            progress_callback: Optional callback for progress updates
        """
        self.max_workers = max_workers
        self.progress_callback = progress_callback
        self.progress = ProcessingProgress(0, 0, 0)

    async def process_files(
        self,
        file_paths: List[str],
        process_func: Callable,
        *args,
        **kwargs
    ) -> List[ProcessingResult]:
        """
        Process files in parallel.

        Args:
            file_paths: List of file paths to process
            process_func: Async function to process each file
                         Signature: async def process_func(file_path, *args, **kwargs)
            *args, **kwargs: Additional arguments for process_func

        Returns:
            List of ProcessingResult objects (one per file)
        """
        if not file_paths:
            return []

        # Initialize progress
        self.progress = ProcessingProgress(
            total_files=len(file_paths),
            processed_files=0,
            failed_files=0,
            start_time=datetime.now()
        )

        logger.info(
            f"Starting parallel processing: {len(file_paths)} files, "
            f"{self.max_workers} workers"
        )

        # Use semaphore to limit concurrent tasks
        semaphore = asyncio.Semaphore(self.max_workers)

        async def process_with_semaphore(file_path: str) -> ProcessingResult:
            """Process single file with semaphore and error handling"""
            async with semaphore:
                return await self._process_single_file(
                    file_path=file_path,
                    process_func=process_func,
                    args=args,
                    kwargs=kwargs
                )

        # Create tasks for all files
        tasks = [process_with_semaphore(fp) for fp in file_paths]

        # Execute all tasks concurrently with progress tracking
        results = await asyncio.gather(*tasks, return_exceptions=False)

        # Log summary
        successful = sum(1 for r in results if r.success)
        failed = len(results) - successful
        duration = self.progress.elapsed_seconds

        logger.info(
            f"Parallel processing complete: {successful}/{len(file_paths)} successful, "
            f"{failed} failed, {duration:.2f}s total, "
            f"{self.progress.files_per_second:.2f} files/sec"
        )

        return results

    async def _process_single_file(
        self,
        file_path: str,
        process_func: Callable,
        args: tuple,
        kwargs: dict
    ) -> ProcessingResult:
        """
        Process single file with timing and error handling.

        Args:
            file_path: Path to file
            process_func: Processing function
            args: Additional positional args
            kwargs: Additional keyword args

        Returns:
            ProcessingResult with success/failure info
        """
        start_time = datetime.now()
        self.progress.current_file = file_path

        try:
            # Call processing function
            result = await process_func(file_path, *args, **kwargs)

            # Success
            self.progress.processed_files += 1
            duration = (datetime.now() - start_time).total_seconds()

            # Notify progress callback
            if self.progress_callback:
                self.progress_callback(self.progress)

            return ProcessingResult(
                file_path=file_path,
                success=True,
                result=result,
                duration_seconds=duration
            )

        except Exception as e:
            # Failure (isolated - doesn't affect other files)
            self.progress.processed_files += 1
            self.progress.failed_files += 1
            duration = (datetime.now() - start_time).total_seconds()

            logger.error(f"Failed to process {file_path}: {e}")

            # Notify progress callback
            if self.progress_callback:
                self.progress_callback(self.progress)

            return ProcessingResult(
                file_path=file_path,
                success=False,
                error=e,
                duration_seconds=duration
            )

    def get_progress(self) -> ProcessingProgress:
        """
        Get current processing progress.

        Returns:
            ProcessingProgress with current stats
        """
        return self.progress


class BatchProcessor:
    """
    Process items in batches with concurrency control.

    Example:
        processor = BatchProcessor(batch_size=50, max_concurrent_batches=3)

        async def process_batch(items):
            # Process batch of items
            return results

        results = await processor.process_batches(
            items=[1, 2, 3, ...],
            process_func=process_batch
        )
    """

    def __init__(
        self,
        batch_size: int = 50,
        max_concurrent_batches: int = 3
    ):
        """
        Initialize batch processor.

        Args:
            batch_size: Number of items per batch
            max_concurrent_batches: Maximum concurrent batch processing tasks
        """
        self.batch_size = batch_size
        self.max_concurrent_batches = max_concurrent_batches

    async def process_batches(
        self,
        items: List[Any],
        process_func: Callable,
        *args,
        **kwargs
    ) -> List[Any]:
        """
        Process items in batches.

        Args:
            items: List of items to process
            process_func: Async function to process batch
                         Signature: async def process_func(batch, *args, **kwargs)
            *args, **kwargs: Additional arguments for process_func

        Returns:
            Flattened list of results from all batches
        """
        if not items:
            return []

        # Create batches
        batches = [
            items[i:i + self.batch_size]
            for i in range(0, len(items), self.batch_size)
        ]

        logger.info(
            f"Processing {len(items)} items in {len(batches)} batches "
            f"(size={self.batch_size}, concurrent={self.max_concurrent_batches})"
        )

        # Use semaphore for concurrency control
        semaphore = asyncio.Semaphore(self.max_concurrent_batches)

        async def process_with_semaphore(batch: List[Any], batch_num: int) -> List[Any]:
            """Process single batch with semaphore"""
            async with semaphore:
                logger.debug(f"Processing batch {batch_num + 1}/{len(batches)}")
                return await process_func(batch, *args, **kwargs)

        # Process all batches concurrently (limited by semaphore)
        tasks = [
            process_with_semaphore(batch, i)
            for i, batch in enumerate(batches)
        ]

        batch_results = await asyncio.gather(*tasks)

        # Flatten results
        results = []
        for batch_result in batch_results:
            if isinstance(batch_result, list):
                results.extend(batch_result)
            else:
                results.append(batch_result)

        logger.info(f"Batch processing complete: {len(results)} total results")

        return results


class ProgressTracker:
    """
    Track progress of long-running operations with logging.

    Example:
        tracker = ProgressTracker(total=1000, log_interval=100)

        for i in range(1000):
            # Do work
            tracker.increment()  # Logs every 100 items
    """

    def __init__(
        self,
        total: int,
        log_interval: int = 100,
        operation_name: str = "Processing"
    ):
        """
        Initialize progress tracker.

        Args:
            total: Total number of items to process
            log_interval: Log progress every N items
            operation_name: Name of operation for logging
        """
        self.total = total
        self.log_interval = log_interval
        self.operation_name = operation_name
        self.current = 0
        self.start_time = datetime.now()
        self.last_log_at = 0

    def increment(self, count: int = 1):
        """
        Increment progress counter.

        Args:
            count: Number to increment by
        """
        self.current += count

        # Log if interval reached
        if self.current - self.last_log_at >= self.log_interval:
            self._log_progress()
            self.last_log_at = self.current

    def _log_progress(self):
        """Log current progress"""
        percent = (self.current / self.total) * 100 if self.total > 0 else 0
        elapsed = (datetime.now() - self.start_time).total_seconds()
        rate = self.current / elapsed if elapsed > 0 else 0

        logger.info(
            f"{self.operation_name}: {self.current}/{self.total} "
            f"({percent:.1f}%) - {rate:.1f} items/sec"
        )

    def complete(self):
        """Log completion"""
        elapsed = (datetime.now() - self.start_time).total_seconds()
        rate = self.current / elapsed if elapsed > 0 else 0

        logger.info(
            f"{self.operation_name} complete: {self.current}/{self.total} items "
            f"in {elapsed:.2f}s ({rate:.1f} items/sec)"
        )
