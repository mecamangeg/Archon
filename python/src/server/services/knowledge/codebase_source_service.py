# File: python/src/server/services/knowledge/codebase_source_service.py

from typing import Dict, Optional
from datetime import datetime
import uuid
import logging

logger = logging.getLogger(__name__)


class CodebaseSourceService:
    """
    Manages knowledge sources for project codebases.

    Each project with a linked codebase gets a dedicated source in the knowledge base.
    """

    def __init__(self, db):
        self.db = db

    async def get_or_create_codebase_source(
        self,
        project_id: str,
        project_title: str
    ) -> str:
        """
        Get existing codebase source for project or create new one.

        Args:
            project_id: Project UUID
            project_title: Project title for source naming

        Returns:
            source_id: UUID of the codebase source
        """
        source_name = f"project_codebase_{project_id}"

        # Check if source exists
        result = self.db.table('archon_sources')\
            .select('source_id')\
            .eq('metadata->>project_id', project_id)\
            .execute()

        if result.data and len(result.data) > 0:
            return result.data[0]['source_id']

        # Create new source
        source_id = str(uuid.uuid4())
        insert_result = self.db.table('archon_sources')\
            .insert({
                'source_id': source_id,
                'source_url': f"project://{project_id}",
                'source_display_name': f"{project_title} (Codebase)",
                'title': f"{project_title} Codebase",
                'summary': f"Codebase for project {project_title}",
                'metadata': {
                    'project_id': project_id,
                    'auto_synced': True,
                    'source_type': 'codebase',
                    'created_at': datetime.now().isoformat()
                }
            })\
            .execute()

        logger.info(f"Created codebase source {source_id} for project {project_id}")
        return source_id

    async def get_source_stats(self, source_id: str) -> Dict:
        """
        Get statistics for a codebase source.

        Returns:
            Dict with total_files, total_chunks, last_update
        """
        # Count chunks
        chunks_result = self.db.table('knowledge_chunks')\
            .select('id', count='exact')\
            .eq('source_id', source_id)\
            .execute()

        total_chunks = chunks_result.count or 0

        # Get unique file count from metadata
        files_result = await self.db.rpc(
            'count_unique_files',
            {'src_id': source_id}
        ).execute()

        total_files = files_result.data if files_result.data else 0

        # Get last update timestamp
        last_update_result = await self.db.table('knowledge_chunks')\
            .select('created_at')\
            .eq('source_id', source_id)\
            .order('created_at', desc=True)\
            .limit(1)\
            .execute()

        last_update = None
        if last_update_result.data and len(last_update_result.data) > 0:
            last_update = last_update_result.data[0]['created_at']

        return {
            'total_files': total_files,
            'total_chunks': total_chunks,
            'last_update': last_update
        }

    async def delete_codebase_source(self, source_id: str) -> None:
        """
        Delete codebase source and all associated chunks.

        Args:
            source_id: UUID of the source to delete
        """
        # Delete chunks (cascade should handle this, but explicit is safer)
        await self.db.table('knowledge_chunks')\
            .delete()\
            .eq('source_id', source_id)\
            .execute()

        # Delete source
        await self.db.table('knowledge_sources')\
            .delete()\
            .eq('source_id', source_id)\
            .execute()

        logger.info(f"Deleted codebase source {source_id}")
