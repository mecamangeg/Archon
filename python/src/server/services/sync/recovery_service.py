"""
Sync recovery mechanisms for production reliability.

Provides:
- Checkpoint-based recovery (resume from failure point)
- Data integrity verification
- Orphaned chunk cleanup
- Rollback capability
- Sync resume after failures
"""

import asyncio
from dataclasses import dataclass, asdict
from typing import List, Dict, Optional
from datetime import datetime
import logging
import os
import uuid

logger = logging.getLogger(__name__)


@dataclass
class SyncCheckpoint:
    """Checkpoint for sync recovery"""
    id: str
    project_id: str
    sync_job_id: str
    files_processed: List[str]
    files_remaining: List[str]
    chunks_created: List[str]
    status: str  # 'active', 'completed', 'failed', 'rolled_back'
    created_at: datetime


@dataclass
class IntegrityCheckResult:
    """Result from integrity verification"""
    valid: bool
    issues: List[str]
    orphaned_chunks: int
    duplicate_chunks: int
    missing_embeddings: int


class RecoveryService:
    """
    Service for sync recovery and integrity checks.

    Features:
    - Create checkpoints during sync
    - Resume sync from last checkpoint
    - Verify data integrity
    - Cleanup orphaned chunks
    - Rollback corrupted syncs
    """

    def __init__(self, db, sync_service):
        """
        Initialize recovery service.

        Args:
            db: Supabase client for database access
            sync_service: IncrementalSyncService instance
        """
        self.db = db
        self.sync_service = sync_service

    async def create_checkpoint(
        self,
        project_id: str,
        sync_job_id: str,
        files_processed: List[str],
        files_remaining: List[str],
        chunks_created: List[str]
    ) -> str:
        """
        Create sync checkpoint for recovery.

        Args:
            project_id: Project UUID
            sync_job_id: Unique sync job identifier
            files_processed: List of file paths already processed
            files_remaining: List of file paths still to process
            chunks_created: List of chunk IDs created so far

        Returns:
            Checkpoint ID
        """
        checkpoint_id = str(uuid.uuid4())

        checkpoint_data = {
            'files_processed': files_processed,
            'files_remaining': files_remaining,
            'chunks_created': chunks_created,
            'timestamp': datetime.now().isoformat()
        }

        try:
            await self.db.table('sync_checkpoints').insert({
                'id': checkpoint_id,
                'project_id': project_id,
                'sync_job_id': sync_job_id,
                'checkpoint_data': checkpoint_data,
                'status': 'active'
            }).execute()

            logger.info(
                f"Checkpoint created: {checkpoint_id} for project {project_id} "
                f"({len(files_processed)} processed, {len(files_remaining)} remaining)"
            )

            return checkpoint_id

        except Exception as e:
            logger.error(f"Failed to create checkpoint: {e}")
            raise

    async def resume_from_checkpoint(self, project_id: str) -> bool:
        """
        Resume sync from last checkpoint.

        Args:
            project_id: Project UUID

        Returns:
            True if successfully resumed, False if no checkpoint found
        """
        try:
            # Get most recent active checkpoint
            result = await self.db.table('sync_checkpoints')\
                .select('*')\
                .eq('project_id', project_id)\
                .eq('status', 'active')\
                .order('created_at', desc=True)\
                .limit(1)\
                .execute()

            if not result.data:
                logger.info(f"No active checkpoint found for project {project_id}")
                return False

            checkpoint = result.data[0]
            checkpoint_data = checkpoint['checkpoint_data']
            files_remaining = checkpoint_data.get('files_remaining', [])

            if not files_remaining:
                logger.info("No files remaining in checkpoint. Marking complete.")
                await self._mark_checkpoint_complete(checkpoint['id'])
                return True

            logger.info(
                f"Resuming sync from checkpoint {checkpoint['id']} "
                f"with {len(files_remaining)} files"
            )

            # Resume sync with remaining files
            stats = await self.sync_service.sync_project_changes(
                project_id=project_id,
                changed_files=files_remaining
            )

            # Mark checkpoint complete
            await self._mark_checkpoint_complete(checkpoint['id'])

            logger.info(
                f"Sync resumed and completed: {stats.files_processed} files, "
                f"{stats.chunks_added} chunks added"
            )

            return True

        except Exception as e:
            logger.error(f"Failed to resume sync from checkpoint: {e}")
            return False

    async def verify_sync_integrity(self, project_id: str) -> IntegrityCheckResult:
        """
        Verify data integrity after sync.

        Checks:
        - Orphaned chunks (file no longer exists)
        - Duplicate chunks (same chunk_hash)
        - Missing embeddings (null embedding vectors)

        Args:
            project_id: Project UUID

        Returns:
            IntegrityCheckResult with detailed findings
        """
        issues = []

        try:
            # Get project and source
            project = await self.db.table('projects')\
                .select('*')\
                .eq('id', project_id)\
                .single()\
                .execute()

            if not project.data:
                return IntegrityCheckResult(
                    valid=False,
                    issues=['Project not found'],
                    orphaned_chunks=0,
                    duplicate_chunks=0,
                    missing_embeddings=0
                )

            source_id = project.data.get('codebase_source_id')
            if not source_id:
                return IntegrityCheckResult(
                    valid=False,
                    issues=['No codebase source found'],
                    orphaned_chunks=0,
                    duplicate_chunks=0,
                    missing_embeddings=0
                )

            # Run integrity checks in parallel
            orphaned_task = self._find_orphaned_chunks(project_id, source_id)
            duplicate_task = self._find_duplicate_chunks(source_id)
            missing_task = self._find_missing_embeddings(source_id)

            orphaned_chunks, duplicate_chunks, missing_embeddings = await asyncio.gather(
                orphaned_task,
                duplicate_task,
                missing_task
            )

            # Aggregate issues
            if orphaned_chunks:
                issues.append(f"Found {len(orphaned_chunks)} orphaned chunks")

            if duplicate_chunks:
                issues.append(f"Found {len(duplicate_chunks)} duplicate chunks")

            if missing_embeddings:
                issues.append(f"Found {len(missing_embeddings)} chunks with missing embeddings")

            is_valid = len(issues) == 0

            result = IntegrityCheckResult(
                valid=is_valid,
                issues=issues,
                orphaned_chunks=len(orphaned_chunks),
                duplicate_chunks=len(duplicate_chunks),
                missing_embeddings=len(missing_embeddings)
            )

            if is_valid:
                logger.info(f"Integrity check passed for project {project_id}")
            else:
                logger.warning(
                    f"Integrity check found issues for project {project_id}: {issues}"
                )

            return result

        except Exception as e:
            logger.error(f"Integrity check failed: {e}")
            return IntegrityCheckResult(
                valid=False,
                issues=[f"Integrity check error: {str(e)}"],
                orphaned_chunks=0,
                duplicate_chunks=0,
                missing_embeddings=0
            )

    async def cleanup_orphaned_chunks(self, project_id: str) -> int:
        """
        Remove chunks for files that no longer exist.

        Args:
            project_id: Project UUID

        Returns:
            Number of chunks deleted
        """
        try:
            project = await self.db.table('projects')\
                .select('*')\
                .eq('id', project_id)\
                .single()\
                .execute()

            if not project.data:
                logger.error(f"Project not found: {project_id}")
                return 0

            source_id = project.data.get('codebase_source_id')
            local_path = project.data.get('local_path')

            if not source_id or not local_path:
                logger.error("Project missing source_id or local_path")
                return 0

            orphaned_chunk_ids = await self._find_orphaned_chunks(project_id, source_id)

            if orphaned_chunk_ids:
                # Delete in batches
                BATCH_SIZE = 100
                for i in range(0, len(orphaned_chunk_ids), BATCH_SIZE):
                    batch = orphaned_chunk_ids[i:i + BATCH_SIZE]
                    await self.db.table('knowledge_chunks')\
                        .delete()\
                        .in_('id', batch)\
                        .execute()

                logger.info(
                    f"Cleaned up {len(orphaned_chunk_ids)} orphaned chunks "
                    f"for project {project_id}"
                )

            return len(orphaned_chunk_ids)

        except Exception as e:
            logger.error(f"Failed to cleanup orphaned chunks: {e}")
            return 0

    async def rollback_sync(self, project_id: str, checkpoint_id: str) -> bool:
        """
        Rollback sync to checkpoint state.

        Args:
            project_id: Project UUID
            checkpoint_id: Checkpoint UUID to rollback to

        Returns:
            True if rollback successful
        """
        try:
            # Get checkpoint
            checkpoint = await self.db.table('sync_checkpoints')\
                .select('*')\
                .eq('id', checkpoint_id)\
                .single()\
                .execute()

            if not checkpoint.data:
                logger.error(f"Checkpoint not found: {checkpoint_id}")
                return False

            checkpoint_data = checkpoint.data['checkpoint_data']
            chunks_created = checkpoint_data.get('chunks_created', [])

            # Delete chunks created after checkpoint
            if chunks_created:
                # Delete in batches
                BATCH_SIZE = 100
                for i in range(0, len(chunks_created), BATCH_SIZE):
                    batch = chunks_created[i:i + BATCH_SIZE]
                    await self.db.table('knowledge_chunks')\
                        .delete()\
                        .in_('id', batch)\
                        .execute()

                logger.info(
                    f"Rolled back {len(chunks_created)} chunks for checkpoint {checkpoint_id}"
                )

            # Mark checkpoint as rolled back
            await self.db.table('sync_checkpoints')\
                .update({'status': 'rolled_back'})\
                .eq('id', checkpoint_id)\
                .execute()

            logger.info(f"Rollback successful for checkpoint {checkpoint_id}")
            return True

        except Exception as e:
            logger.error(f"Rollback failed: {e}")
            return False

    async def _find_orphaned_chunks(
        self,
        project_id: str,
        source_id: str
    ) -> List[str]:
        """
        Find chunks for non-existent files.

        Args:
            project_id: Project UUID
            source_id: Codebase source ID

        Returns:
            List of orphaned chunk IDs
        """
        try:
            project = await self.db.table('projects')\
                .select('local_path')\
                .eq('id', project_id)\
                .single()\
                .execute()

            local_path = project.data.get('local_path')
            if not local_path:
                return []

            # Get all chunks with file paths
            chunks = await self.db.table('knowledge_chunks')\
                .select('id, metadata')\
                .eq('source_id', source_id)\
                .execute()

            orphaned = []
            for chunk in chunks.data:
                file_path = chunk.get('metadata', {}).get('file_path')
                if file_path and not os.path.exists(file_path):
                    orphaned.append(chunk['id'])

            return orphaned

        except Exception as e:
            logger.error(f"Failed to find orphaned chunks: {e}")
            return []

    async def _find_duplicate_chunks(self, source_id: str) -> List[str]:
        """
        Find duplicate chunks by chunk_hash.

        Args:
            source_id: Codebase source ID

        Returns:
            List of duplicate chunk hashes
        """
        try:
            # Call database function for duplicate detection
            result = await self.db.rpc(
                'find_duplicate_chunks',
                {'src_id': source_id}
            ).execute()

            if result.data:
                return [row['chunk_hash'] for row in result.data]

            return []

        except Exception as e:
            # Function might not exist yet, silently ignore
            logger.debug(f"Duplicate detection function not available: {e}")
            return []

    async def _find_missing_embeddings(self, source_id: str) -> List[str]:
        """
        Find chunks with null embeddings.

        Args:
            source_id: Codebase source ID

        Returns:
            List of chunk IDs with missing embeddings
        """
        try:
            result = await self.db.table('knowledge_chunks')\
                .select('id')\
                .eq('source_id', source_id)\
                .is_('embedding', 'null')\
                .execute()

            return [chunk['id'] for chunk in result.data]

        except Exception as e:
            logger.error(f"Failed to find missing embeddings: {e}")
            return []

    async def _mark_checkpoint_complete(self, checkpoint_id: str):
        """Mark checkpoint as completed"""
        try:
            await self.db.table('sync_checkpoints')\
                .update({'status': 'completed'})\
                .eq('id', checkpoint_id)\
                .execute()
        except Exception as e:
            logger.error(f"Failed to mark checkpoint complete: {e}")

    async def _mark_checkpoint_failed(self, checkpoint_id: str, error_message: str):
        """Mark checkpoint as failed"""
        try:
            await self.db.table('sync_checkpoints')\
                .update({
                    'status': 'failed',
                    'checkpoint_data': {'error': error_message}
                })\
                .eq('id', checkpoint_id)\
                .execute()
        except Exception as e:
            logger.error(f"Failed to mark checkpoint failed: {e}")
