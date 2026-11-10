"""
Genuine MCP Client implementation using the official MCP Python SDK.
Connects via StdioServerParameters transport, discovers tools, handles timeouts,
parses structured tool responses, and logs execution metadata to SQLite.
"""
import asyncio
import json
import os
import sys
import time
import uuid
from contextlib import AsyncExitStack
from pathlib import Path
from typing import Any, Dict, List, Optional

from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client
from mcp.types import Tool as MCPTool

from devpilot.config import settings
from devpilot.db.database import get_db


class MCPClientError(Exception):
    """Base exception for MCP client errors."""
    pass


class MCPConnectionError(MCPClientError):
    """Raised when failing to establish or maintain an MCP connection."""
    pass


class MCPToolExecutionError(MCPClientError):
    """Raised when an MCP tool invocation fails or returns an error."""
    pass


class DevPilotMCPClient:
    """
    Client for managing sessions with the DevPilot Repository MCP Server.
    Provides tool discovery, invocation, structured error handling, and audit logging.
    """

    def __init__(
        self,
        repo_root: Optional[Path] = None,
        session_id: Optional[str] = None,
        custom_python: Optional[str] = None,
    ):
        self.repo_root = (repo_root or settings.DEFAULT_REPO_ROOT).resolve()
        self.session_id = session_id or f"session_{uuid.uuid4().hex[:8]}"
        self.python_executable = custom_python or sys.executable
        
        self._exit_stack: Optional[AsyncExitStack] = None
        self._session: Optional[ClientSession] = None
        self._discovered_tools: Dict[str, MCPTool] = {}
        self.is_connected = False

    async def connect(self) -> None:
        """Establishes an official MCP session over stdio transport."""
        if self.is_connected:
            return

        project_dir = Path(__file__).resolve().parent.parent.parent
        env = os.environ.copy()
        env["PYTHONPATH"] = f"{str(project_dir)}{os.pathsep}{env.get('PYTHONPATH', '')}"

        server_params = StdioServerParameters(
            command=self.python_executable,
            args=[
                "-m",
                "devpilot.mcp_server.server",
                "--repo-root",
                str(self.repo_root),
                "--session-id",
                self.session_id,
            ],
            env=env,
        )

        try:
            self._exit_stack = AsyncExitStack()
            read, write = await self._exit_stack.enter_async_context(stdio_client(server_params))
            self._session = await self._exit_stack.enter_async_context(ClientSession(read, write))
            
            # MCP initialize handshake
            await self._session.initialize()
            self.is_connected = True
            
            # Discover tools immediately
            await self.discover_tools()

        except Exception as e:
            await self.disconnect()
            raise MCPConnectionError(f"Failed to establish MCP connection: {str(e)}") from e

    async def disconnect(self) -> None:
        """Closes the MCP session and cleans up resources."""
        self.is_connected = False
        self._session = None
        if self._exit_stack:
            try:
                await self._exit_stack.aclose()
            except Exception:
                pass
            self._exit_stack = None

    async def discover_tools(self) -> List[MCPTool]:
        """Discovers available tools from the connected MCP server."""
        if not self.is_connected or not self._session:
            raise MCPConnectionError("MCP Client is not connected to any server.")

        try:
            tools_response = await self._session.list_tools()
            self._discovered_tools = {t.name: t for t in tools_response.tools}
            return list(self._discovered_tools.values())
        except Exception as e:
            raise MCPClientError(f"Error discovering MCP tools: {str(e)}") from e

    def get_tool_schema(self, tool_name: str) -> Optional[MCPTool]:
        """Returns the cached schema of a discovered tool."""
        return self._discovered_tools.get(tool_name)

    async def call_tool(
        self,
        tool_name: str,
        arguments: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Invokes an MCP tool by name with arguments.
        Records execution metadata, timing, and results in SQLite execution trace.
        """
        if not self.is_connected or not self._session:
            raise MCPConnectionError("Cannot call tool: MCP Client is not connected.")

        args = arguments or {}
        call_id = f"mcp_call_{uuid.uuid4().hex[:8]}"
        start_time = time.time()
        db = get_db()

        try:
            # Official MCP SDK invocation
            result = await self._session.call_tool(tool_name, args)
            duration_ms = int((time.time() - start_time) * 1000)

            # Process content blocks
            parsed_content = None
            raw_text = ""
            for block in result.content:
                if block.type == "text":
                    raw_text += block.text
                    try:
                        parsed_content = json.loads(block.text)
                    except Exception:
                        pass

            final_data = parsed_content if parsed_content is not None else {"raw_output": raw_text}

            # Check for error flag in MCP response
            status = "ERROR" if getattr(result, "is_error", False) else "SUCCESS"
            err_msg = raw_text if status == "ERROR" else None

            # Persist in SQLite execution trace
            db.record_tool_call(
                call_id=call_id,
                session_id=self.session_id,
                tool_name=tool_name,
                arguments=args,
                result=final_data,
                status=status,
                duration_ms=duration_ms,
                error_message=err_msg,
            )

            if status == "ERROR":
                raise MCPToolExecutionError(f"Tool '{tool_name}' returned an error: {err_msg}")

            return final_data

        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            db.record_tool_call(
                call_id=call_id,
                session_id=self.session_id,
                tool_name=tool_name,
                arguments=args,
                result={"error": str(e)},
                status="ERROR",
                duration_ms=duration_ms,
                error_message=str(e),
            )
            if isinstance(e, MCPClientError):
                raise
            raise MCPToolExecutionError(f"Failed to invoke MCP tool '{tool_name}': {str(e)}") from e

    async def __aenter__(self):
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.disconnect()
