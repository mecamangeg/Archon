# File: python/src/server/services/sync/incremental_sync_service.py

from typing import List, Dict, Set, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass, field
import os
import logging
import traceback

from .hash_utils import compute_file_hash, compute_chunk_hash
from .chunker import Chunker, detect_language
from ..knowledge.codebase_source_service import CodebaseSourceService
from ..projects.project_service import ProjectService
from .error_handler import (
    retry_with_backoff,
    RetryConfig,
    CircuitBreaker,
    CircuitBreakerOpenError,
    ErrorClassifier,
    SyncErrorLogger,
    handle_sync_error
)
from .parallel_processor import ParallelFileProcessor, ProcessingProgress
from .batch_embedder import BatchEmbedder

logger = logging.getLogger(__name__)


@dataclass
class FileChangeEvent:
    """Represents a file change"""
    file_path: str
    change_type: str  # 'added', 'modified', 'deleted'
    timestamp: datetime


@dataclass
class SyncStats:
    """Statistics from a sync operation"""
    files_processed: int = 0
    chunks_added: int = 0
    chunks_modified: int = 0
    chunks_deleted: int = 0
    duration_seconds: float = 0.0
    errors: List[str] = field(default_factory=list)


class IncrementalSyncService:
    """
    Manages incremental synchronization of project codebases.

    Workflow:
    1. Detect changed files (via watcher, git hooks, or manual trigger)
    2. Load existing chunks for those files from database
    3. Compute content hashes to detect actual changes
    4. Re-chunk only changed files
    5. Update embeddings for new/modified chunks
    6. Delete chunks for deleted files
    7. Sync to database with transaction
    """

    def __init__(
        self,
        db,
        embedding_service,
        project_service: ProjectService,
        codebase_source_service: CodebaseSourceService
    ):
        self.db = db
        self.embedding_service = embedding_service
        self.project_service = project_service
        self.codebase_source_service = codebase_source_service
        self.chunker = Chunker()

        # Error handling components
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}  # project_id -> breaker
        self.error_logger = SyncErrorLogger(db)
        self.error_classifier = ErrorClassifier()

        # Performance optimization components
        self.parallel_processor = ParallelFileProcessor(
            max_workers=5,
            progress_callback=self._on_progress_update
        )
        self.batch_embedder = BatchEmbedder(
            embedding_service=self.embedding_service,
            batch_size=50,
            rate_limit=10,
            rate_window=1.0
        )

    def _on_progress_update(self, progress: ProcessingProgress):
        """
        Callback for progress updates during parallel processing.

        Args:
            progress: Current processing progress
        """
        logger.info(
            f"Sync progress: {progress.processed_files}/{progress.total_files} files "
            f"({progress.percent_complete:.1f}%), {progress.failed_files} failed, "
            f"{progress.files_per_second:.2f} files/sec, "
            f"ETA: {progress.estimated_seconds_remaining:.0f}s"
        )

    def _get_circuit_breaker(self, project_id: str) -> CircuitBreaker:
        """
        Get or create circuit breaker for project.

        Args:
            project_id: Project UUID

        Returns:
            Circuit breaker instance for the project
        """
        if project_id not in self.circuit_breakers:
            self.circuit_breakers[project_id] = CircuitBreaker(
                failure_threshold=5,
                timeout=300.0,  # 5 minutes
                half_open_max_calls=1
            )
        return self.circuit_breakers[project_id]

    async def sync_project_changes(
        self,
        project_id: str,
        changed_files: Optional[List[str]] = None
    ) -> SyncStats:
        """
        Incrementally sync changes for a project with circuit breaker protection.

        Args:
            project_id: Project UUID
            changed_files: Optional list of specific files to sync.
                          If None, scans entire project directory.

        Returns:
            SyncStats with metrics about the sync operation

        Raises:
            CircuitBreakerOpenError: If circuit breaker is open due to repeated failures
        """
        breaker = self._get_circuit_breaker(project_id)

        try:
            # Execute sync through circuit breaker
            # Pass coroutine directly instead of lambda to avoid async issues
            async def sync_wrapper():
                return await self._sync_project_changes_internal(project_id, changed_files)

            result = await breaker.call(sync_wrapper)
            return result

        except CircuitBreakerOpenError as e:
            logger.warning(f"Circuit breaker open for project {project_id}: {e}")

            # Log circuit breaker error
            await self.error_logger.log_error(
                project_id=project_id,
                error_type='circuit_breaker',
                error_message=str(e),
                error_details={
                    'state': 'open',
                    'failure_count': breaker.failure_count
                }
            )

            # Update project status
            await self.project_service.update_project_sync_status(
                project_id=project_id,
                status='error',
                error_message=str(e)
            )

            raise

    async def _sync_project_changes_internal(
        self,
        project_id: str,
        changed_files: Optional[List[str]] = None
    ) -> SyncStats:
        """
        Internal sync implementation (called by circuit breaker).

        Args:
            project_id: Project UUID
            changed_files: Optional list of specific files to sync

        Returns:
            SyncStats with metrics about the sync operation
        """
        start_time = datetime.now()
        stats = SyncStats()

        try:
            # Update status to 'syncing'
            await self.project_service.update_project_sync_status(
                project_id=project_id,
                status='syncing'
            )

            # Get project metadata
            success, result = self.project_service.get_project(project_id)
            if not success or not result.get('project'):
                raise ValueError(f"Project not found: {project_id}")

            project = result['project']

            local_path = project.get('local_path')
            if not local_path:
                raise ValueError(f"Project {project_id} has no local_path configured")

            # Get or create codebase source
            source_id = await self.codebase_source_service.get_or_create_codebase_source(
                project_id=project_id,
                project_title=project.get('title', 'Unknown Project')
            )

            # Update project with source_id
            self.project_service.update_project(project_id, {
                'codebase_source_id': source_id
            })

            # If no specific files provided, scan entire directory
            if changed_files is None:
                changed_files = self._scan_directory(local_path)
                logger.info(f"Scanning entire directory: {len(changed_files)} files found")

            # Categorize changes
            added_files, modified_files, deleted_files = await self._categorize_changes(
                source_id=source_id,
                local_path=local_path,
                file_paths=changed_files
            )

            logger.info(
                f"Changes detected - Added: {len(added_files)}, "
                f"Modified: {len(modified_files)}, Deleted: {len(deleted_files)}"
            )

            # Process deletions
            for file_path in deleted_files:
                try:
                    deleted_count = await self._delete_file_chunks(source_id, file_path)
                    stats.chunks_deleted += deleted_count
                except Exception as e:
                    logger.error(f"Error deleting chunks for {file_path}: {e}")
                    stats.errors.append(f"Delete error ({file_path}): {str(e)}")

            # Process additions in parallel
            if added_files:
                logger.info(f"Processing {len(added_files)} new files in parallel...")

                add_results = await self.parallel_processor.process_files(
                    file_paths=added_files,
                    process_func=self._chunk_and_embed_file,
                    source_id=source_id,
                    base_path=local_path,
                    project_id=project_id
                )

                # Aggregate results
                for result in add_results:
                    if result.success and result.result:
                        chunks = result.result
                        await self._insert_chunks(chunks)
                        stats.chunks_added += len(chunks)
                        stats.files_processed += 1
                    else:
                        # Log error
                        if result.error:
                            error_info = handle_sync_error(
                                error=result.error,
                                context={'file_path': result.file_path, 'operation': 'add_file'}
                            )

                            await self.error_logger.log_error(
                                project_id=project_id,
                                error_type=error_info['error_type'],
                                error_message=error_info['error_message'],
                                error_details=error_info['context'],
                                file_path=result.file_path
                            )

                            stats.errors.append(f"Add error ({result.file_path}): {error_info['user_message']}")

            # Process modifications in parallel (with chunk-level diffing)
            if modified_files:
                logger.info(f"Processing {len(modified_files)} modified files in parallel...")

                modify_results = await self.parallel_processor.process_files(
                    file_paths=modified_files,
                    process_func=self._process_modified_file,
                    source_id=source_id,
                    base_path=local_path,
                    project_id=project_id
                )

                # Aggregate results
                for result in modify_results:
                    if result.success and result.result:
                        to_delete, to_add = result.result

                        await self._delete_chunks(to_delete)
                        await self._insert_chunks(to_add)

                        stats.chunks_modified += len(to_add)
                        stats.chunks_deleted += len(to_delete)
                        stats.files_processed += 1
                    else:
                        # Log error
                        if result.error:
                            error_info = handle_sync_error(
                                error=result.error,
                                context={'file_path': result.file_path, 'operation': 'modify_file'}
                            )

                            await self.error_logger.log_error(
                                project_id=project_id,
                                error_type=error_info['error_type'],
                                error_message=error_info['error_message'],
                                error_details=error_info['context'],
                                file_path=result.file_path
                            )

                            stats.errors.append(f"Modify error ({result.file_path}): {error_info['user_message']}")

            # Update project sync status
            await self.project_service.update_project_sync_status(
                project_id=project_id,
                status='completed' if not stats.errors else 'error',
                last_sync_at=datetime.now(),
                error_message='; '.join(stats.errors[:3]) if stats.errors else None
            )

            stats.duration_seconds = (datetime.now() - start_time).total_seconds()

            logger.info(
                f"Sync completed for project {project_id} - "
                f"{stats.files_processed} files, {stats.chunks_added} added, "
                f"{stats.chunks_modified} modified, {stats.chunks_deleted} deleted, "
                f"{stats.duration_seconds:.2f}s"
            )

            return stats

        except Exception as e:
            logger.error(f"Sync failed for project {project_id}: {e}")
            await self.project_service.update_project_sync_status(
                project_id=project_id,
                status='error',
                error_message=str(e)
            )
            raise

    def _scan_directory(self, directory: str) -> List[str]:
        """
        Scan directory for all relevant files.

        Args:
            directory: Root directory to scan

        Returns:
            List of absolute file paths
        """
        relevant_files = []

        # Extensions to include
        include_extensions = {
            '.py', '.ts', '.tsx', '.js', '.jsx', '.md', '.mdx',
            '.rs', '.go', '.java', '.cpp', '.c', '.cs', '.rb',
            '.php', '.swift', '.kt', '.json', '.yaml', '.yml',
            '.toml', '.sql', '.sh', '.bash'
        }

        # Directories to exclude
        exclude_dirs = {
            '.git', 'node_modules', '__pycache__', '.venv', 'venv',
            'dist', 'build', '.next', 'target', '.pytest_cache',
            'coverage', '.nyc_output', 'vendor'
        }

        for root, dirs, files in os.walk(directory):
            # Remove excluded directories
            dirs[:] = [d for d in dirs if d not in exclude_dirs]

            for file in files:
                # Check extension
                if any(file.endswith(ext) for ext in include_extensions):
                    file_path = os.path.join(root, file)
                    relevant_files.append(file_path)

        return relevant_files

    async def _categorize_changes(
        self,
        source_id: str,
        local_path: str,
        file_paths: List[str]
    ) -> Tuple[List[str], List[str], List[str]]:
        """
        Categorize files into added, modified, or deleted.

        Args:
            source_id: Codebase source ID
            local_path: Project root path
            file_paths: List of file paths to check

        Returns:
            Tuple of (added_files, modified_files, deleted_files)
        """
        added_files = []
        modified_files = []
        deleted_files = []

        for file_path in file_paths:
            # Check if file exists
            if not os.path.exists(file_path):
                deleted_files.append(file_path)
                continue

            # Get existing chunks for this file
            existing_chunks = await self._get_chunks_for_file(source_id, file_path)

            if not existing_chunks:
                # No existing chunks = new file
                added_files.append(file_path)
            else:
                # Check if content changed via hash
                current_hash = compute_file_hash(file_path)
                old_hash = existing_chunks[0].get('metadata', {}).get('file_hash')

                if current_hash != old_hash:
                    modified_files.append(file_path)
                # else: No change, skip

        return added_files, modified_files, deleted_files

    async def _process_modified_file(
        self,
        file_path: str,
        source_id: str,
        base_path: str,
        project_id: Optional[str] = None
    ) -> Tuple[List[str], List[Dict]]:
        """
        Process modified file with chunk-level diffing.

        Args:
            file_path: Absolute path to file
            source_id: Codebase source ID
            base_path: Project root path
            project_id: Project UUID (for error logging)

        Returns:
            Tuple of (chunk_ids_to_delete, chunks_to_add)
        """
        # Get old chunks
        old_chunks = await self._get_chunks_for_file(source_id, file_path)

        # Generate new chunks
        new_chunks = await self._chunk_and_embed_file(
            file_path=file_path,
            source_id=source_id,
            base_path=base_path,
            project_id=project_id
        )

        # Compute minimal diff
        to_delete, to_add = self._compute_chunk_diff(old_chunks, new_chunks)

        return to_delete, to_add

    async def _chunk_and_embed_file(
        self,
        file_path: str,
        source_id: str,
        base_path: str,
        project_id: Optional[str] = None
    ) -> List[Dict]:
        """
        Chunk file content and generate embeddings with error handling.

        Args:
            file_path: Absolute path to file
            source_id: Codebase source ID
            base_path: Project root path
            project_id: Project UUID (for error logging)

        Returns:
            List of chunk dictionaries ready for database insertion
        """
        # Read file
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except UnicodeDecodeError:
            # Skip binary files
            logger.warning(f"Skipping binary file: {file_path}")
            return []
        except Exception as e:
            # Handle file read errors
            error_info = handle_sync_error(
                error=e,
                context={'file_path': file_path, 'operation': 'file_read'}
            )

            await self.error_logger.log_error(
                project_id=project_id,
                error_type=error_info['error_type'],
                error_message=error_info['error_message'],
                error_details=error_info['context'],
                file_path=file_path
            )

            logger.error(f"Failed to read file {file_path}: {error_info['user_message']}")
            return []

        # Detect language
        language = detect_language(file_path)

        # Compute file hash
        file_hash = compute_file_hash(file_path)

        # Chunk content
        code_chunks = self.chunker.chunk_file(content, language)

        if not code_chunks:
            return []

        # Batch embed all chunks (more efficient than one-by-one)
        try:
            chunk_texts = [chunk.content for chunk in code_chunks]
            embeddings = await self.batch_embedder.embed_batch(chunk_texts)

            # Build chunk objects with embeddings
            chunk_objects = []
            for idx, (code_chunk, embedding) in enumerate(zip(code_chunks, embeddings)):
                if not embedding:
                    # Skip chunk if embedding failed
                    logger.warning(f"Skipping chunk {idx} of {file_path} (embedding failed)")
                    continue

                # Compute chunk hash
                chunk_hash = compute_chunk_hash(code_chunk.content)

                chunk_objects.append({
                    'source_id': source_id,
                    'content': code_chunk.content,
                    'embedding': embedding,
                    'metadata': {
                        'file_path': file_path,
                        'relative_path': os.path.relpath(file_path, base_path),
                        'file_hash': file_hash,
                        'chunk_hash': chunk_hash,
                        'language': language,
                        'chunk_index': idx,
                        'start_line': code_chunk.start_line,
                        'end_line': code_chunk.end_line,
                        'section_type': code_chunk.section_type,
                        'section_name': code_chunk.section_name
                    }
                })

            return chunk_objects

        except Exception as e:
            error_info = handle_sync_error(
                error=e,
                context={
                    'file_path': file_path,
                    'operation': 'batch_embedding',
                    'num_chunks': len(code_chunks)
                }
            )

            await self.error_logger.log_error(
                project_id=project_id,
                error_type=error_info['error_type'],
                error_message=error_info['error_message'],
                error_details=error_info['context'],
                file_path=file_path
            )

            logger.error(f"Error batch embedding {file_path}: {error_info['user_message']}")

            # Fallback: try individual embedding with retry
            logger.info(f"Falling back to individual embedding for {file_path}")
            return await self._chunk_and_embed_file_individually(
                code_chunks=code_chunks,
                file_path=file_path,
                source_id=source_id,
                base_path=base_path,
                file_hash=file_hash,
                language=language,
                project_id=project_id
            )

    async def _chunk_and_embed_file_individually(
        self,
        code_chunks: List,
        file_path: str,
        source_id: str,
        base_path: str,
        file_hash: str,
        language: str,
        project_id: Optional[str] = None
    ) -> List[Dict]:
        """
        Fallback method: embed chunks individually (slower but more reliable).

        Args:
            code_chunks: List of code chunks from chunker
            file_path: Absolute path to file
            source_id: Codebase source ID
            base_path: Project root path
            file_hash: File hash
            language: Programming language
            project_id: Project UUID (for error logging)

        Returns:
            List of chunk dictionaries
        """
        chunk_objects = []

        for idx, code_chunk in enumerate(code_chunks):
            try:
                # Generate embedding with retry logic
                embedding = await self._embed_with_retry(
                    content=code_chunk.content,
                    file_path=file_path,
                    chunk_index=idx,
                    project_id=project_id
                )

                if not embedding:
                    # Skip chunk if embedding failed after retries
                    continue

                # Compute chunk hash
                chunk_hash = compute_chunk_hash(code_chunk.content)

                chunk_objects.append({
                    'source_id': source_id,
                    'content': code_chunk.content,
                    'embedding': embedding,
                    'metadata': {
                        'file_path': file_path,
                        'relative_path': os.path.relpath(file_path, base_path),
                        'file_hash': file_hash,
                        'chunk_hash': chunk_hash,
                        'language': language,
                        'chunk_index': idx,
                        'start_line': code_chunk.start_line,
                        'end_line': code_chunk.end_line,
                        'section_type': code_chunk.section_type,
                        'section_name': code_chunk.section_name
                    }
                })
            except Exception as e:
                error_info = handle_sync_error(
                    error=e,
                    context={
                        'file_path': file_path,
                        'chunk_index': idx,
                        'operation': 'chunk_embedding'
                    }
                )

                await self.error_logger.log_error(
                    project_id=project_id,
                    error_type=error_info['error_type'],
                    error_message=error_info['error_message'],
                    error_details=error_info['context'],
                    file_path=file_path
                )

                logger.error(f"Error embedding chunk {idx} of {file_path}: {error_info['user_message']}")
                # Continue with remaining chunks

        return chunk_objects

    @retry_with_backoff(RetryConfig(max_retries=3, initial_delay=1.0, max_delay=30.0))
    async def _embed_with_retry(
        self,
        content: str,
        file_path: str,
        chunk_index: int,
        project_id: Optional[str] = None
    ) -> Optional[list]:
        """
        Generate embedding with automatic retry logic.

        Args:
            content: Text content to embed
            file_path: Source file path (for logging)
            chunk_index: Chunk index in file (for logging)
            project_id: Project UUID (for error logging)

        Returns:
            Embedding vector or None if all retries failed
        """
        try:
            return await self.embedding_service.embed(content)
        except Exception as e:
            error_type = self.error_classifier.classify(e)

            # Log error (retry decorator will handle retrying)
            if not self.error_classifier.is_retryable(error_type):
                # Don't retry non-retryable errors
                logger.error(
                    f"Non-retryable error embedding chunk {chunk_index} of {file_path}: {e}"
                )
                return None

            # Retry will happen automatically for retryable errors
            raise

    async def _get_chunks_for_file(
        self,
        source_id: str,
        file_path: str
    ) -> List[Dict]:
        """
        Retrieve existing chunks for a file.

        Args:
            source_id: Codebase source ID
            file_path: Absolute path to file

        Returns:
            List of existing chunks
        """
        result = self.db.table('knowledge_chunks')\
            .select('*')\
            .eq('source_id', source_id)\
            .eq('metadata->>file_path', file_path)\
            .execute()

        return result.data if result.data else []

    async def _delete_file_chunks(
        self,
        source_id: str,
        file_path: str
    ) -> int:
        """
        Delete all chunks for a file.

        Args:
            source_id: Codebase source ID
            file_path: Absolute path to file

        Returns:
            Number of chunks deleted
        """
        result = self.db.table('knowledge_chunks')\
            .delete()\
            .eq('source_id', source_id)\
            .eq('metadata->>file_path', file_path)\
            .execute()

        count = len(result.data) if result.data else 0
        logger.info(f"Deleted {count} chunks for {file_path}")
        return count

    def _compute_chunk_diff(
        self,
        old_chunks: List[Dict],
        new_chunks: List[Dict]
    ) -> Tuple[List[str], List[Dict]]:
        """
        Compute minimal diff between old and new chunks using content hashing.

        Args:
            old_chunks: Existing chunks from database
            new_chunks: New chunks from re-chunking

        Returns:
            Tuple of (chunk_ids_to_delete, chunks_to_add)
        """
        # Build hash maps
        old_by_hash = {
            chunk['metadata'].get('chunk_hash'): chunk
            for chunk in old_chunks
            if chunk.get('metadata', {}).get('chunk_hash')
        }

        new_by_hash = {
            chunk['metadata'].get('chunk_hash'): chunk
            for chunk in new_chunks
            if chunk.get('metadata', {}).get('chunk_hash')
        }

        # Find differences
        old_hashes = set(old_by_hash.keys())
        new_hashes = set(new_by_hash.keys())

        deleted_hashes = old_hashes - new_hashes
        added_hashes = new_hashes - old_hashes

        # Get chunk IDs to delete
        chunks_to_delete_ids = [
            old_by_hash[h]['id']
            for h in deleted_hashes
            if h in old_by_hash
        ]

        # Get chunks to add
        chunks_to_add = [
            new_by_hash[h]
            for h in added_hashes
            if h in new_by_hash
        ]

        logger.debug(
            f"Chunk diff: {len(chunks_to_delete_ids)} to delete, "
            f"{len(chunks_to_add)} to add"
        )

        return chunks_to_delete_ids, chunks_to_add

    async def _delete_chunks(self, chunk_ids: List[str]) -> None:
        """
        Delete chunks by ID.

        Args:
            chunk_ids: List of chunk IDs to delete
        """
        if not chunk_ids:
            return

        self.db.table('knowledge_chunks')\
            .delete()\
            .in_('id', chunk_ids)\
            .execute()

        logger.info(f"Deleted {len(chunk_ids)} chunks")

    async def _insert_chunks(self, chunks: List[Dict]) -> None:
        """
        Insert new chunks into database.

        Args:
            chunks: List of chunk dictionaries
        """
        if not chunks:
            return

        # Batch insert
        BATCH_SIZE = 50
        for i in range(0, len(chunks), BATCH_SIZE):
            batch = chunks[i:i + BATCH_SIZE]
            self.db.table('knowledge_chunks')\
                .insert(batch)\
                .execute()

        logger.info(f"Inserted {len(chunks)} chunks")
