"""
Pydantic Models for MCP Tool Inputs and Structured Outputs
"""
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


# 1. inspect_repository
class InspectRepositoryInput(BaseModel):
    repo_path: Optional[str] = Field(
        default=None,
        description="Optional relative or absolute repository path. Defaults to configured root."
    )


class InspectRepositoryOutput(BaseModel):
    repo_name: str
    root_path: str
    is_git: bool
    branch: Optional[str] = None
    head_commit: Optional[str] = None
    file_count: int
    languages: List[str]
    top_level_entries: List[str]
    readme_excerpt: Optional[str] = None


# 2. list_files
class ListFilesInput(BaseModel):
    directory: str = Field(
        default="",
        description="Relative directory path inside repository. Empty string for root."
    )
    pattern: Optional[str] = Field(
        default=None,
        description="Glob pattern filter (e.g. '*.py', '**/*.json')."
    )
    recursive: bool = Field(
        default=False,
        description="Whether to scan recursively into subdirectories."
    )
    max_results: int = Field(
        default=100,
        description="Maximum number of files to return."
    )


class FileEntry(BaseModel):
    path: str
    name: str
    is_directory: bool
    size_bytes: int


class ListFilesOutput(BaseModel):
    base_directory: str
    files: List[FileEntry]
    total_count: int


# 3. read_file
class ReadFileInput(BaseModel):
    file_path: str = Field(
        description="Relative path of file inside repository to inspect."
    )
    start_line: Optional[int] = Field(
        default=1,
        ge=1,
        description="1-based starting line number."
    )
    end_line: Optional[int] = Field(
        default=None,
        ge=1,
        description="1-based ending line number (inclusive)."
    )


class ReadFileOutput(BaseModel):
    file_path: str
    total_lines: int
    start_line: int
    end_line: int
    content: str


# 4. search_code
class SearchCodeInput(BaseModel):
    query: str = Field(
        description="Text or regex to search across repository files."
    )
    file_pattern: Optional[str] = Field(
        default=None,
        description="Optional glob filter (e.g. '*.py')."
    )
    max_results: int = Field(
        default=50,
        description="Maximum matching snippets to return."
    )
    is_regex: bool = Field(
        default=False,
        description="Whether query is a regular expression."
    )


class SearchMatch(BaseModel):
    file_path: str
    line_number: int
    line_content: str


class SearchCodeOutput(BaseModel):
    query: str
    matches: List[SearchMatch]
    total_matches: int


# 5. run_tests
class RunTestsInput(BaseModel):
    command: str = Field(
        default="pytest -v --tb=short",
        description="Allowlisted test command to execute. Must match allowlisted prefixes."
    )
    test_path: Optional[str] = Field(
        default=None,
        description="Optional specific test file or directory path relative to repo root."
    )
    timeout_seconds: Optional[int] = Field(
        default=20,
        le=60,
        description="Subprocess timeout in seconds."
    )


class TestFailure(BaseModel):
    __test__ = False
    test_id: str
    message: str


class RunTestsOutput(BaseModel):
    command: str
    exit_code: int
    passed: int
    failed: int
    skipped: int
    total: int
    duration_seconds: float
    output: str
    failures: List[TestFailure]


# 6. get_git_status
class GetGitStatusInput(BaseModel):
    repo_path: Optional[str] = Field(
        default=None,
        description="Optional target repo path. Defaults to configured root."
    )


class GetGitStatusOutput(BaseModel):
    clean: bool
    branch: str
    untracked: List[str]
    modified: List[str]
    staged: List[str]


# 7. get_git_diff
class GetGitDiffInput(BaseModel):
    staged: bool = Field(
        default=False,
        description="If True, inspect staged diff; otherwise unstaged working tree diff."
    )
    file_path: Optional[str] = Field(
        default=None,
        description="Optional specific relative file path to diff."
    )


class GetGitDiffOutput(BaseModel):
    has_diff: bool
    diff: str
    files_changed: List[str]


# 8. propose_patch
class ProposePatchInput(BaseModel):
    target_file: str = Field(
        description="Relative path of file to be patched."
    )
    diff: str = Field(
        description="Unified diff format or code replacement proposing the modification."
    )
    rationale: str = Field(
        description="Detailed technical reasoning explaining why this patch fixes the bug."
    )


class ProposePatchOutput(BaseModel):
    patch_id: str
    target_file: str
    rationale: str
    status: str
    diff_preview: str
    approval_token: str
    instructions: str
