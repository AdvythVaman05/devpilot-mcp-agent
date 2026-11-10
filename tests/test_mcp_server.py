"""
Unit Tests for DevPilot MCP Server Tools
Tests each of the 8 MCP tools individually with real arguments.
"""
from pathlib import Path
import pytest

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
from devpilot.security import PathTraversalError


def test_inspect_repository(temp_repo):
    """inspect_repository tool returns accurate structure and metadata."""
    res = tool_inspect_repository(temp_repo, InspectRepositoryInput())
    assert res.repo_name == temp_repo.name
    assert "Python" in res.languages
    assert res.file_count > 0
    assert any("auth_service" in entry for entry in res.top_level_entries)
    assert res.readme_excerpt is not None


def test_list_files(temp_repo):
    """list_files lists files and respects pattern and recursion filters."""
    # Flat listing
    res = tool_list_files(temp_repo, ListFilesInput(directory="", recursive=False))
    names = [f.name for f in res.files]
    assert "README.md" in names

    # Recursive Python files
    res_py = tool_list_files(temp_repo, ListFilesInput(directory="", pattern="*.py", recursive=True))
    py_paths = [f.path for f in res_py.files]
    assert any("auth.py" in p for p in py_paths)


def test_read_file(temp_repo):
    """read_file reads specific line ranges and calculates line counts."""
    res = tool_read_file(temp_repo, ReadFileInput(file_path="auth_service/models.py", start_line=1, end_line=10))
    assert res.total_lines > 10
    assert res.start_line == 1
    assert res.end_line == 10
    assert "class User:" in res.content


def test_read_file_nonexistent_raises(temp_repo):
    """Reading non-existent file raises FileNotFoundError."""
    with pytest.raises(FileNotFoundError):
        tool_read_file(temp_repo, ReadFileInput(file_path="nonexistent.py"))


def test_search_code(temp_repo):
    """search_code finds matches with file and line numbers."""
    res = tool_search_code(temp_repo, SearchCodeInput(query="TokenExpiredError"))
    assert res.total_matches > 0
    match_files = [m.file_path for m in res.matches]
    assert any("auth.py" in f for f in match_files)


def test_search_code_regex(temp_repo):
    """search_code supports regular expressions."""
    res = tool_search_code(temp_repo, SearchCodeInput(query=r"def\s+verify_token", is_regex=True))
    assert res.total_matches > 0
    assert "auth.py" in res.matches[0].file_path


def test_run_tests_failure_capture(temp_repo):
    """run_tests captures the intentional baseline test failure with details."""
    res = tool_run_tests(temp_repo, RunTestsInput(command="pytest -v --tb=short"))
    assert res.exit_code == 1
    assert res.failed == 1
    assert res.passed == 3
    assert len(res.failures) >= 1
    assert "test_valid_token_verification" in res.failures[0].test_id


def test_run_tests_timeout_handling(temp_repo, monkeypatch):
    """run_tests handles timeout expired gracefully."""
    import subprocess
    def mock_subprocess_run(*args, **kwargs):
        raise subprocess.TimeoutExpired(cmd=args[0], timeout=1)

    monkeypatch.setattr(subprocess, "run", mock_subprocess_run)
    res = tool_run_tests(temp_repo, RunTestsInput(command="pytest -v"))
    assert res.exit_code == -1
    assert "timed out" in res.output.lower()
    assert res.failures[0].test_id == "timeout"


def test_get_git_status(temp_repo):
    """get_git_status reports branch and modified/untracked files."""
    res = tool_get_git_status(temp_repo, GetGitStatusInput())
    assert res.branch in ("master", "main", "non-git")


def test_get_git_diff_clean(temp_repo):
    """get_git_diff on clean working tree reports no diff."""
    res = tool_get_git_diff(temp_repo, GetGitDiffInput())
    assert res.has_diff is False


def test_propose_patch_creates_token(temp_repo):
    """propose_patch returns pending approval output and does NOT modify files."""
    target_file = temp_repo / "auth_service" / "auth.py"
    with open(target_file, "r", encoding="utf-8") as f:
        original_content = f.read()

    res = tool_propose_patch(
        temp_repo,
        ProposePatchInput(
            target_file="auth_service/auth.py",
            diff="--- a\n+++ b",
            rationale="Fix inverted comparison operator"
        )
    )

    assert res.status == "PENDING_APPROVAL"
    assert res.approval_token is not None
    assert len(res.approval_token) == 64  # SHA256 length

    # Ensure file on disk was NOT touched
    with open(target_file, "r", encoding="utf-8") as f:
        current_content = f.read()
    assert original_content == current_content
