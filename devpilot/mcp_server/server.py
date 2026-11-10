"""
DevPilot Custom Repository MCP Server
Exposes 8 core tools adhering to the Model Context Protocol (MCP).
Sandboxed strictly to configured repository root.
"""
import argparse
import asyncio
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from mcp.server.mcpserver import MCPServer

from devpilot.config import settings
from devpilot.mcp_server.models import (
    InspectRepositoryInput,
    ListFilesInput,
    ReadFileInput,
    SearchCodeInput,
    RunTestsInput,
    GetGitStatusInput,
    GetGitDiffInput,
    ProposePatchInput,
)
from devpilot.mcp_server.tools import (
    tool_inspect_repository,
    tool_list_files,
    tool_read_file,
    tool_search_code,
    tool_run_tests,
    tool_get_git_status,
    tool_get_git_diff,
    tool_propose_patch,
)


def create_mcp_server(repo_root: Optional[Path] = None, session_id: Optional[str] = None) -> MCPServer:
    """Creates and configures an MCP server instance with the 8 repository tools."""
    effective_root = (repo_root or settings.DEFAULT_REPO_ROOT).resolve()
    
    server = MCPServer(
        name="devpilot-repository-server",
        version="1.0.0",
        instructions="DevPilot Repository MCP Server. Provides read-only repository inspection, "
                     "allowlisted test execution, and safe patch proposals for software engineering agents."
    )

    @server.tool(
        name="inspect_repository",
        description="Inspects high-level repository structure, git state, detected languages, and README overview."
    )
    def inspect_repository(repo_path: Optional[str] = None) -> Dict[str, Any]:
        """Inspects repository architecture and metadata."""
        inp = InspectRepositoryInput(repo_path=repo_path)
        out = tool_inspect_repository(effective_root, inp)
        return out.model_dump()

    @server.tool(
        name="list_files",
        description="Lists files and subdirectories inside the repository with optional glob pattern filter."
    )
    def list_files(
        directory: str = "",
        pattern: Optional[str] = None,
        recursive: bool = False,
        max_results: int = 100,
    ) -> Dict[str, Any]:
        """Lists files inside the repository."""
        inp = ListFilesInput(
            directory=directory,
            pattern=pattern,
            recursive=recursive,
            max_results=max_results,
        )
        out = tool_list_files(effective_root, inp)
        return out.model_dump()

    @server.tool(
        name="read_file",
        description="Reads lines from an allowlisted source file inside the repository with optional line ranges."
    )
    def read_file(
        file_path: str,
        start_line: Optional[int] = 1,
        end_line: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Reads file contents safely."""
        inp = ReadFileInput(
            file_path=file_path,
            start_line=start_line,
            end_line=end_line,
        )
        out = tool_read_file(effective_root, inp)
        return out.model_dump()

    @server.tool(
        name="search_code",
        description="Searches for text or regex across text files in the repository, returning matching snippets."
    )
    def search_code(
        query: str,
        file_pattern: Optional[str] = None,
        max_results: int = 50,
        is_regex: bool = False,
    ) -> Dict[str, Any]:
        """Searches code for matching patterns."""
        inp = SearchCodeInput(
            query=query,
            file_pattern=file_pattern,
            max_results=max_results,
            is_regex=is_regex,
        )
        out = tool_search_code(effective_root, inp)
        return out.model_dump()

    @server.tool(
        name="run_tests",
        description="Executes allowlisted pytest suite inside the repository with strict timeout and captures failure tracebacks."
    )
    def run_tests(
        command: str = "pytest -v --tb=short",
        test_path: Optional[str] = None,
        timeout_seconds: Optional[int] = 20,
    ) -> Dict[str, Any]:
        """Executes repository tests safely."""
        inp = RunTestsInput(
            command=command,
            test_path=test_path,
            timeout_seconds=timeout_seconds,
        )
        out = tool_run_tests(effective_root, inp)
        return out.model_dump()

    @server.tool(
        name="get_git_status",
        description="Inspects git repository status including modified, untracked, and staged files."
    )
    def get_git_status(repo_path: Optional[str] = None) -> Dict[str, Any]:
        """Inspects git status."""
        inp = GetGitStatusInput(repo_path=repo_path)
        out = tool_get_git_status(effective_root, inp)
        return out.model_dump()

    @server.tool(
        name="get_git_diff",
        description="Inspects git diff for unstaged or staged changes across the repository or a specific file."
    )
    def get_git_diff(
        staged: bool = False,
        file_path: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Inspects git diff."""
        inp = GetGitDiffInput(staged=staged, file_path=file_path)
        out = tool_get_git_diff(effective_root, inp)
        return out.model_dump()

    @server.tool(
        name="propose_patch",
        description="Proposes a code patch without applying it. Generates an approval token and diff preview. Requires human authorization."
    )
    def propose_patch(
        target_file: str,
        diff: str,
        rationale: str,
    ) -> Dict[str, Any]:
        """Proposes a code fix for human review."""
        inp = ProposePatchInput(
            target_file=target_file,
            diff=diff,
            rationale=rationale,
        )
        out = tool_propose_patch(effective_root, inp, session_id=session_id)
        return out.model_dump()

    return server


async def run_stdio() -> None:
    """Runs the MCP server over standard I/O (stdio transport)."""
    parser = argparse.ArgumentParser(description="DevPilot MCP Repository Server")
    parser.add_argument("--repo-root", type=str, default=None, help="Root path of target repository")
    parser.add_argument("--session-id", type=str, default=None, help="Current investigation session ID")
    args = parser.parse_args()

    repo_root = Path(args.repo_root) if args.repo_root else None
    server = create_mcp_server(repo_root=repo_root, session_id=args.session_id)
    await server.run_stdio_async()


if __name__ == "__main__":
    asyncio.run(run_stdio())
