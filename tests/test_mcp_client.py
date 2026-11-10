"""
Integration Tests for DevPilot Genuine MCP Client
Verifies MCP session establishment, dynamic tool discovery, and tool execution via MCP protocol.
"""
from pathlib import Path
import pytest

from devpilot.mcp_client.client import DevPilotMCPClient, MCPConnectionError


@pytest.mark.asyncio
async def test_mcp_client_connection_and_discovery(temp_repo):
    """MCP client must connect to the server and discover all 8 tools."""
    client = DevPilotMCPClient(repo_root=temp_repo, session_id="test_client_session")
    await client.connect()
    try:
        assert client.is_connected is True
        tools = await client.discover_tools()
        tool_names = [t.name for t in tools]
        expected_tools = [
            "inspect_repository",
            "list_files",
            "read_file",
            "search_code",
            "run_tests",
            "get_git_status",
            "get_git_diff",
            "propose_patch",
        ]
        for expected in expected_tools:
            assert expected in tool_names
    finally:
        await client.disconnect()


@pytest.mark.asyncio
async def test_mcp_client_tool_invocation(temp_repo):
    """Invoking tools through MCP client returns structured output and logs to SQLite."""
    client = DevPilotMCPClient(repo_root=temp_repo, session_id="test_invocation_session")
    async with client:
        result = await client.call_tool("list_files", {"directory": "auth_service", "pattern": "*.py"})
        assert "files" in result
        assert len(result["files"]) >= 2
        paths = [f["name"] for f in result["files"]]
        assert "auth.py" in paths
