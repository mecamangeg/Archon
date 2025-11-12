"""
MCP Project Sync Tools for Archon
Phase 5, Task 5.2

Model Context Protocol (MCP) tool definitions for project synchronization.
These tools allow AI assistants to interact with Archon's project sync functionality.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from src.server.config.logfire_config import get_logger
from src.server.services.sync.incremental_sync_service import IncrementalSyncService
from src.server.services.knowledge.codebase_source_service import CodebaseSourceService
from src.server.services.search.project_code_search import ProjectCodeSearchService
from src.server.utils import get_supabase_client

logger = get_logger(__name__)


# Tool Input Schemas
class SyncProjectCodebaseInput(BaseModel):
    """Input schema for sync_project_codebase tool"""

    project_id: str = Field(..., description="UUID of the project to sync")
    trigger: str = Field(
        default="manual",
        description="Source of sync trigger: manual, auto, git-hook",
    )
    changed_files: Optional[List[str]] = Field(
        default=None,
        description="Optional list of specific files to sync",
    )


class SearchProjectCodeInput(BaseModel):
    """Input schema for search_project_code tool"""

    project_id: str = Field(..., description="UUID of the project to search")
    query: str = Field(..., description="Search query (semantic search)")
    match_count: int = Field(default=5, description="Number of results to return")
    file_filter: Optional[str] = Field(
        default=None,
        description="Optional file pattern filter (e.g., '*.py')",
    )


class GetProjectSyncStatusInput(BaseModel):
    """Input schema for get_project_sync_status tool"""

    project_id: str = Field(..., description="UUID of the project")


class ListProjectFilesInput(BaseModel):
    """Input schema for list_project_files tool"""

    project_id: str = Field(..., description="UUID of the project")
    file_filter: Optional[str] = Field(
        default=None,
        description="Optional file pattern filter",
    )


class GetFileContentInput(BaseModel):
    """Input schema for get_file_content tool"""

    project_id: str = Field(..., description="UUID of the project")
    file_path: str = Field(..., description="Path to file relative to project root")


# MCP Tool Definitions
MCP_TOOLS = [
    {
        "name": "sync_project_codebase",
        "description": "Trigger synchronization of a project's codebase to the knowledge base",
        "inputSchema": {
            "type": "object",
            "properties": {
                "project_id": {
                    "type": "string",
                    "description": "UUID of the project to sync",
                },
                "trigger": {
                    "type": "string",
                    "enum": ["manual", "auto", "git-hook"],
                    "description": "Source of sync trigger",
                    "default": "manual",
                },
                "changed_files": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optional list of specific files to sync",
                },
            },
            "required": ["project_id"],
        },
    },
    {
        "name": "search_project_code",
        "description": "Search for code within a project's synced codebase",
        "inputSchema": {
            "type": "object",
            "properties": {
                "project_id": {
                    "type": "string",
                    "description": "UUID of the project to search",
                },
                "query": {
                    "type": "string",
                    "description": "Search query (semantic search)",
                },
                "match_count": {
                    "type": "integer",
                    "default": 5,
                    "description": "Number of results to return",
                },
                "file_filter": {
                    "type": "string",
                    "description": "Optional file pattern filter (e.g., '*.py')",
                },
            },
            "required": ["project_id", "query"],
        },
    },
    {
        "name": "get_project_sync_status",
        "description": "Get synchronization status for a project",
        "inputSchema": {
            "type": "object",
            "properties": {
                "project_id": {
                    "type": "string",
                    "description": "UUID of the project",
                },
            },
            "required": ["project_id"],
        },
    },
    {
        "name": "list_project_files",
        "description": "List all files in a synced project",
        "inputSchema": {
            "type": "object",
            "properties": {
                "project_id": {
                    "type": "string",
                    "description": "UUID of the project",
                },
                "file_filter": {
                    "type": "string",
                    "description": "Optional file pattern filter",
                },
            },
            "required": ["project_id"],
        },
    },
    {
        "name": "get_file_content",
        "description": "Get content of a specific file from a synced project",
        "inputSchema": {
            "type": "object",
            "properties": {
                "project_id": {
                    "type": "string",
                    "description": "UUID of the project",
                },
                "file_path": {
                    "type": "string",
                    "description": "Path to file relative to project root",
                },
            },
            "required": ["project_id", "file_path"],
        },
    },
]


# Tool Handler Functions
async def sync_project_codebase_handler(
    input_data: SyncProjectCodebaseInput,
) -> Dict[str, Any]:
    """
    Handler for sync_project_codebase MCP tool

    Args:
        input_data: Validated input data

    Returns:
        Sync result dict
    """
    try:
        db = get_supabase_client()
        sync_service = IncrementalSyncService(db)

        # Trigger sync
        result = await sync_service.sync_project(
            project_id=input_data.project_id,
            trigger=input_data.trigger,
            changed_files=input_data.changed_files,
        )

        logger.info(
            f"MCP tool sync_project_codebase completed",
            extra={"project_id": input_data.project_id, "trigger": input_data.trigger},
        )

        return {
            "success": True,
            "project_id": input_data.project_id,
            "result": result,
        }

    except Exception as e:
        logger.error(f"Error in sync_project_codebase handler: {str(e)}")
        return {
            "success": False,
            "error": str(e),
        }


async def search_project_code_handler(
    input_data: SearchProjectCodeInput,
) -> Dict[str, Any]:
    """
    Handler for search_project_code MCP tool

    Args:
        input_data: Validated input data

    Returns:
        Search results dict
    """
    try:
        db = get_supabase_client()
        search_service = ProjectCodeSearchService(db)

        # Perform search
        results = await search_service.search(
            project_id=input_data.project_id,
            query=input_data.query,
            match_count=input_data.match_count,
            file_filter=input_data.file_filter,
        )

        logger.info(
            f"MCP tool search_project_code completed",
            extra={
                "project_id": input_data.project_id,
                "query": input_data.query,
                "results_count": len(results),
            },
        )

        return {
            "success": True,
            "results": results,
            "count": len(results),
        }

    except Exception as e:
        logger.error(f"Error in search_project_code handler: {str(e)}")
        return {
            "success": False,
            "error": str(e),
        }


async def get_project_sync_status_handler(
    input_data: GetProjectSyncStatusInput,
) -> Dict[str, Any]:
    """
    Handler for get_project_sync_status MCP tool

    Args:
        input_data: Validated input data

    Returns:
        Sync status dict
    """
    try:
        db = get_supabase_client()
        codebase_service = CodebaseSourceService(db)

        # Get codebase source for project
        source = await codebase_service.get_by_project_id(input_data.project_id)

        if not source:
            return {
                "success": False,
                "error": "Project not synced yet",
            }

        # Get sync status
        status = {
            "project_id": input_data.project_id,
            "source_id": source.get("id"),
            "last_synced": source.get("last_synced_at"),
            "total_files": source.get("total_files", 0),
            "total_chunks": source.get("total_chunks", 0),
            "sync_enabled": source.get("sync_enabled", False),
        }

        logger.info(
            f"MCP tool get_project_sync_status completed",
            extra={"project_id": input_data.project_id},
        )

        return {
            "success": True,
            "status": status,
        }

    except Exception as e:
        logger.error(f"Error in get_project_sync_status handler: {str(e)}")
        return {
            "success": False,
            "error": str(e),
        }


async def list_project_files_handler(
    input_data: ListProjectFilesInput,
) -> Dict[str, Any]:
    """
    Handler for list_project_files MCP tool

    Args:
        input_data: Validated input data

    Returns:
        List of files dict
    """
    try:
        db = get_supabase_client()
        codebase_service = CodebaseSourceService(db)

        # Get codebase source
        source = await codebase_service.get_by_project_id(input_data.project_id)

        if not source:
            return {
                "success": False,
                "error": "Project not synced yet",
            }

        # Query distinct file paths
        query = db.table("knowledge_chunks").select("file_path").eq("source_id", source["id"])

        if input_data.file_filter:
            query = query.like("file_path", input_data.file_filter)

        response = await query.execute()

        # Get unique file paths
        file_paths = list(set([item["file_path"] for item in response.data]))

        logger.info(
            f"MCP tool list_project_files completed",
            extra={"project_id": input_data.project_id, "files_count": len(file_paths)},
        )

        return {
            "success": True,
            "files": file_paths,
            "count": len(file_paths),
        }

    except Exception as e:
        logger.error(f"Error in list_project_files handler: {str(e)}")
        return {
            "success": False,
            "error": str(e),
        }


async def get_file_content_handler(
    input_data: GetFileContentInput,
) -> Dict[str, Any]:
    """
    Handler for get_file_content MCP tool

    Args:
        input_data: Validated input data

    Returns:
        File content dict
    """
    try:
        db = get_supabase_client()
        codebase_service = CodebaseSourceService(db)

        # Get codebase source
        source = await codebase_service.get_by_project_id(input_data.project_id)

        if not source:
            return {
                "success": False,
                "error": "Project not synced yet",
            }

        # Query file chunks
        response = (
            await db.table("knowledge_chunks")
            .select("*")
            .eq("source_id", source["id"])
            .eq("file_path", input_data.file_path)
            .order("chunk_index")
            .execute()
        )

        if not response.data:
            return {
                "success": False,
                "error": f"File not found: {input_data.file_path}",
            }

        # Reconstruct file content from chunks
        chunks = response.data
        content = "\n".join([chunk["content"] for chunk in chunks])

        logger.info(
            f"MCP tool get_file_content completed",
            extra={
                "project_id": input_data.project_id,
                "file_path": input_data.file_path,
                "chunks_count": len(chunks),
            },
        )

        return {
            "success": True,
            "file_path": input_data.file_path,
            "content": content,
            "language": chunks[0].get("language") if chunks else None,
            "chunks_count": len(chunks),
        }

    except Exception as e:
        logger.error(f"Error in get_file_content handler: {str(e)}")
        return {
            "success": False,
            "error": str(e),
        }


# Tool registry mapping tool names to handlers
TOOL_HANDLERS = {
    "sync_project_codebase": sync_project_codebase_handler,
    "search_project_code": search_project_code_handler,
    "get_project_sync_status": get_project_sync_status_handler,
    "list_project_files": list_project_files_handler,
    "get_file_content": get_file_content_handler,
}
