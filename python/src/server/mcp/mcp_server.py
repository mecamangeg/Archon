"""
MCP Server Implementation for Archon
Phase 5, Task 5.2

Implements JSON-RPC 2.0 server for Model Context Protocol (MCP) tools.
"""

import json
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ValidationError

from src.server.config.logfire_config import get_logger
from src.server.mcp.project_sync_tools import MCP_TOOLS, TOOL_HANDLERS

logger = get_logger(__name__)


# JSON-RPC 2.0 Models
class JSONRPCRequest(BaseModel):
    """JSON-RPC 2.0 request"""

    jsonrpc: str = "2.0"
    method: str
    params: Optional[Dict[str, Any]] = None
    id: Optional[str | int] = None


class JSONRPCResponse(BaseModel):
    """JSON-RPC 2.0 response"""

    jsonrpc: str = "2.0"
    result: Optional[Any] = None
    error: Optional[Dict[str, Any]] = None
    id: Optional[str | int] = None


class JSONRPCError(BaseModel):
    """JSON-RPC 2.0 error object"""

    code: int
    message: str
    data: Optional[Any] = None


# JSON-RPC Error Codes
class ErrorCodes:
    """Standard JSON-RPC error codes"""

    PARSE_ERROR = -32700
    INVALID_REQUEST = -32600
    METHOD_NOT_FOUND = -32601
    INVALID_PARAMS = -32602
    INTERNAL_ERROR = -32603


class MCPServer:
    """
    Model Context Protocol Server

    Implements JSON-RPC 2.0 server for MCP tools.
    """

    def __init__(self):
        """Initialize MCP server"""
        self.tools = {}
        self.handlers = {}
        self._register_tools()

    def _register_tools(self):
        """Register all MCP tools"""
        for tool in MCP_TOOLS:
            tool_name = tool["name"]
            self.tools[tool_name] = tool

            if tool_name in TOOL_HANDLERS:
                self.handlers[tool_name] = TOOL_HANDLERS[tool_name]

        logger.info(f"Registered {len(self.tools)} MCP tools")

    def list_tools(self) -> List[Dict[str, Any]]:
        """
        List all available MCP tools

        Returns:
            List of tool definitions
        """
        return list(self.tools.values())

    def get_tool(self, tool_name: str) -> Optional[Dict[str, Any]]:
        """
        Get tool definition by name

        Args:
            tool_name: Name of the tool

        Returns:
            Tool definition or None if not found
        """
        return self.tools.get(tool_name)

    async def call_tool(self, tool_name: str, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Call an MCP tool

        Args:
            tool_name: Name of the tool to call
            input_data: Input parameters for the tool

        Returns:
            Tool result dict

        Raises:
            ValueError: If tool not found or invalid input
        """
        if tool_name not in self.handlers:
            raise ValueError(f"Tool not found: {tool_name}")

        handler = self.handlers[tool_name]

        try:
            # Validate input against tool schema
            # (In production, use jsonschema or similar for validation)

            # Call handler
            result = await handler(input_data)
            return result

        except ValidationError as e:
            logger.error(f"Validation error calling tool {tool_name}: {str(e)}")
            raise ValueError(f"Invalid input parameters: {str(e)}")

        except Exception as e:
            logger.error(f"Error calling tool {tool_name}: {str(e)}")
            raise

    async def handle_request(self, request_data: str) -> str:
        """
        Handle JSON-RPC 2.0 request

        Args:
            request_data: JSON-RPC request string

        Returns:
            JSON-RPC response string
        """
        try:
            # Parse request
            try:
                request_dict = json.loads(request_data)
            except json.JSONDecodeError as e:
                return self._create_error_response(
                    None,
                    ErrorCodes.PARSE_ERROR,
                    "Parse error",
                    str(e),
                )

            # Validate request
            try:
                request = JSONRPCRequest(**request_dict)
            except ValidationError as e:
                return self._create_error_response(
                    request_dict.get("id"),
                    ErrorCodes.INVALID_REQUEST,
                    "Invalid request",
                    str(e),
                )

            # Handle method
            if request.method == "tools/list":
                result = self.list_tools()
                return self._create_success_response(request.id, result)

            elif request.method == "tools/call":
                if not request.params:
                    return self._create_error_response(
                        request.id,
                        ErrorCodes.INVALID_PARAMS,
                        "Missing parameters",
                    )

                tool_name = request.params.get("name")
                input_data = request.params.get("arguments", {})

                if not tool_name:
                    return self._create_error_response(
                        request.id,
                        ErrorCodes.INVALID_PARAMS,
                        "Missing tool name",
                    )

                try:
                    result = await self.call_tool(tool_name, input_data)
                    return self._create_success_response(request.id, result)

                except ValueError as e:
                    return self._create_error_response(
                        request.id,
                        ErrorCodes.INVALID_PARAMS,
                        str(e),
                    )

                except Exception as e:
                    return self._create_error_response(
                        request.id,
                        ErrorCodes.INTERNAL_ERROR,
                        "Internal error",
                        str(e),
                    )

            else:
                return self._create_error_response(
                    request.id,
                    ErrorCodes.METHOD_NOT_FOUND,
                    f"Method not found: {request.method}",
                )

        except Exception as e:
            logger.error(f"Unexpected error handling request: {str(e)}")
            return self._create_error_response(
                None,
                ErrorCodes.INTERNAL_ERROR,
                "Internal error",
                str(e),
            )

    def _create_success_response(self, request_id: Optional[str | int], result: Any) -> str:
        """Create JSON-RPC success response"""
        response = JSONRPCResponse(
            jsonrpc="2.0",
            result=result,
            id=request_id,
        )
        return response.model_dump_json()

    def _create_error_response(
        self,
        request_id: Optional[str | int],
        code: int,
        message: str,
        data: Optional[Any] = None,
    ) -> str:
        """Create JSON-RPC error response"""
        error = JSONRPCError(code=code, message=message, data=data)
        response = JSONRPCResponse(
            jsonrpc="2.0",
            error=error.model_dump(),
            id=request_id,
        )
        return response.model_dump_json()


# Global MCP server instance
mcp_server = MCPServer()
