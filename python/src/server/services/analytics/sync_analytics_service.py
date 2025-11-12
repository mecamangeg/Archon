"""
Sync Analytics Service
Phase 5, Task 5.6
Service for collecting and analyzing project sync metrics
"""

import logging
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from supabase import Client as SupabaseClient

logger = logging.getLogger(__name__)


class SyncAnalyticsService:
    """Service for sync analytics and performance metrics"""

    def __init__(self, db: SupabaseClient):
        self.db = db

    async def record_sync_operation(
        self,
        project_id: str,
        trigger: str,
        started_at: datetime,
        completed_at: Optional[datetime] = None,
        status: str = 'running',
        files_processed: int = 0,
        chunks_added: int = 0,
        chunks_modified: int = 0,
        chunks_deleted: int = 0,
        error_message: Optional[str] = None
    ) -> Dict:
        """
        Record a sync operation for analytics.

        Args:
            project_id: Project UUID
            trigger: Sync trigger source
            started_at: Operation start time
            completed_at: Operation completion time
            status: Operation status
            files_processed: Number of files processed
            chunks_added: Number of chunks added
            chunks_modified: Number of chunks modified
            chunks_deleted: Number of chunks deleted
            error_message: Error message if failed

        Returns:
            Created operation record

        Raises:
            Exception: If database operation fails
        """
        try:
            duration_seconds = None
            if completed_at and started_at:
                duration_seconds = (completed_at - started_at).total_seconds()

            operation = {
                'project_id': project_id,
                'trigger': trigger,
                'started_at': started_at.isoformat(),
                'completed_at': completed_at.isoformat() if completed_at else None,
                'status': status,
                'files_processed': files_processed,
                'chunks_added': chunks_added,
                'chunks_modified': chunks_modified,
                'chunks_deleted': chunks_deleted,
                'duration_seconds': duration_seconds,
                'error_message': error_message
            }

            result = self.db.table('sync_operations').insert(operation).execute()

            logger.info(f"Recorded sync operation for project {project_id}: {status}")

            return result.data[0] if result.data else operation

        except Exception as e:
            logger.error(f"Failed to record sync operation: {e}")
            raise

    async def get_sync_history(
        self,
        project_id: str,
        days: int = 30
    ) -> List[Dict]:
        """
        Get sync operation history for a project.

        Args:
            project_id: Project UUID
            days: Number of days to look back

        Returns:
            List of sync operations sorted by started_at descending
        """
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)

            result = self.db.table('sync_operations') \
                .select('*') \
                .eq('project_id', project_id) \
                .gte('started_at', cutoff_date.isoformat()) \
                .order('started_at', desc=True) \
                .execute()

            return result.data

        except Exception as e:
            logger.error(f"Failed to get sync history: {e}")
            return []

    async def get_performance_metrics(
        self,
        project_id: str,
        days: int = 30
    ) -> Dict:
        """
        Get performance metrics for a project.

        Args:
            project_id: Project UUID
            days: Number of days to analyze

        Returns:
            Dictionary with performance metrics
        """
        try:
            history = await self.get_sync_history(project_id, days)

            if not history:
                return {
                    'total_syncs': 0,
                    'successful_syncs': 0,
                    'failed_syncs': 0,
                    'average_duration': 0.0,
                    'total_files_processed': 0,
                    'total_chunks_added': 0,
                    'total_chunks_modified': 0,
                    'total_chunks_deleted': 0,
                    'success_rate': 0.0,
                    'syncs_by_trigger': {}
                }

            successful = [op for op in history if op['status'] == 'success']
            failed = [op for op in history if op['status'] == 'error']

            durations = [op['duration_seconds'] for op in successful if op.get('duration_seconds')]
            avg_duration = sum(durations) / len(durations) if durations else 0.0

            # Group by trigger
            syncs_by_trigger = {}
            for op in history:
                trigger = op['trigger']
                syncs_by_trigger[trigger] = syncs_by_trigger.get(trigger, 0) + 1

            metrics = {
                'total_syncs': len(history),
                'successful_syncs': len(successful),
                'failed_syncs': len(failed),
                'average_duration': round(avg_duration, 2),
                'total_files_processed': sum(op.get('files_processed', 0) for op in successful),
                'total_chunks_added': sum(op.get('chunks_added', 0) for op in successful),
                'total_chunks_modified': sum(op.get('chunks_modified', 0) for op in successful),
                'total_chunks_deleted': sum(op.get('chunks_deleted', 0) for op in successful),
                'success_rate': round(len(successful) / len(history) * 100, 1) if history else 0.0,
                'syncs_by_trigger': syncs_by_trigger
            }

            return metrics

        except Exception as e:
            logger.error(f"Failed to get performance metrics: {e}")
            return {}

    async def get_error_statistics(
        self,
        project_id: str,
        days: int = 30
    ) -> Dict:
        """
        Get error statistics for a project.

        Args:
            project_id: Project UUID
            days: Number of days to analyze

        Returns:
            Dictionary with error statistics
        """
        try:
            history = await self.get_sync_history(project_id, days)

            failed_ops = [op for op in history if op['status'] == 'error']

            if not failed_ops:
                return {
                    'total_errors': 0,
                    'error_rate': 0.0,
                    'errors_by_trigger': {},
                    'common_errors': []
                }

            # Group errors by trigger
            errors_by_trigger = {}
            for op in failed_ops:
                trigger = op['trigger']
                errors_by_trigger[trigger] = errors_by_trigger.get(trigger, 0) + 1

            # Group errors by message (simplified)
            error_messages = {}
            for op in failed_ops:
                msg = op.get('error_message', 'Unknown error')
                # Truncate long messages
                short_msg = msg[:100] + '...' if len(msg) > 100 else msg
                error_messages[short_msg] = error_messages.get(short_msg, 0) + 1

            # Sort by frequency
            common_errors = sorted(
                [{'message': msg, 'count': count} for msg, count in error_messages.items()],
                key=lambda x: x['count'],
                reverse=True
            )[:5]  # Top 5 errors

            stats = {
                'total_errors': len(failed_ops),
                'error_rate': round(len(failed_ops) / len(history) * 100, 1) if history else 0.0,
                'errors_by_trigger': errors_by_trigger,
                'common_errors': common_errors
            }

            return stats

        except Exception as e:
            logger.error(f"Failed to get error statistics: {e}")
            return {}

    async def get_growth_metrics(
        self,
        project_id: str,
        days: int = 30
    ) -> Dict:
        """
        Get growth metrics showing file/chunk growth over time.

        Args:
            project_id: Project UUID
            days: Number of days to analyze

        Returns:
            Dictionary with growth metrics
        """
        try:
            history = await self.get_sync_history(project_id, days)

            successful = [op for op in history if op['status'] == 'success']

            if not successful:
                return {
                    'growth_by_date': [],
                    'cumulative_files': 0,
                    'cumulative_chunks': 0
                }

            # Group by date
            growth_by_date = {}
            for op in successful:
                date = op['started_at'][:10]  # Extract date (YYYY-MM-DD)
                if date not in growth_by_date:
                    growth_by_date[date] = {
                        'date': date,
                        'files_processed': 0,
                        'chunks_added': 0,
                        'chunks_modified': 0,
                        'chunks_deleted': 0,
                        'syncs_count': 0
                    }

                growth_by_date[date]['files_processed'] += op.get('files_processed', 0)
                growth_by_date[date]['chunks_added'] += op.get('chunks_added', 0)
                growth_by_date[date]['chunks_modified'] += op.get('chunks_modified', 0)
                growth_by_date[date]['chunks_deleted'] += op.get('chunks_deleted', 0)
                growth_by_date[date]['syncs_count'] += 1

            # Convert to list and sort by date
            growth_list = sorted(growth_by_date.values(), key=lambda x: x['date'])

            # Calculate cumulative totals
            cumulative_files = sum(op.get('files_processed', 0) for op in successful)
            cumulative_chunks = sum(op.get('chunks_added', 0) for op in successful)

            metrics = {
                'growth_by_date': growth_list,
                'cumulative_files': cumulative_files,
                'cumulative_chunks': cumulative_chunks
            }

            return metrics

        except Exception as e:
            logger.error(f"Failed to get growth metrics: {e}")
            return {}
