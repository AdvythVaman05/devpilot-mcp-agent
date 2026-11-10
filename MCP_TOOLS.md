# DevPilot Model Context Protocol (MCP) Tool Reference

DevPilot implements a genuine MCP server following the official Model Context Protocol specifications (v2.x) communicating over standard I/O (`stdio` transport). The server exposes 8 strictly typed, sandboxed tools.

---

## 1. `inspect_repository`
Inspects high-level repository structure, git branch, commit hash, detected programming languages, and README overview.

- **Parameters**:
  - `repo_path` *(string, optional)*: Relative or absolute path inside sandbox. Defaults to configured root.
- **Returns**:
  ```json
  {
    "repo_name": "sample_auth_service",
    "root_path": "C:/Projects/DevPilot/sample_repo",
    "is_git": true,
    "branch": "master",
    "head_commit": "db91fc9",
    "file_count": 8,
    "languages": ["Markdown", "Python"],
    "top_level_entries": ["README.md", "auth_service/", "tests/"],
    "readme_excerpt": "# Sample Authentication Service..."
  }
  ```

---

## 2. `list_files`
Lists files and directories inside the repository with optional glob pattern and recursive traversal.

- **Parameters**:
  - `directory` *(string, default: `""`)*: Subdirectory path relative to repository root.
  - `pattern` *(string, optional)*: Glob filter (e.g., `"*.py"`, `"test_*.py"`).
  - `recursive` *(boolean, default: `false`)*: Whether to traverse nested directories.
  - `max_results` *(integer, default: `100`)*: Maximum file entries to return.
- **Returns**:
  ```json
  {
    "base_directory": "",
    "total_count": 3,
    "files": [
      {
        "path": "auth_service/auth.py",
        "name": "auth.py",
        "is_directory": false,
        "size_bytes": 3410
      }
    ]
  }
  ```

---

## 3. `read_file`
Reads lines from an allowlisted source file inside the repository with strict bounds and size guards.

- **Parameters**:
  - `file_path` *(string, required)*: Relative path of file to inspect.
  - `start_line` *(integer, default: `1`)*: 1-based start line.
  - `end_line` *(integer, optional)*: 1-based end line (inclusive).
- **Security Invariant**: Rejects non-existent files, directories, paths outside root, and files exceeding `MAX_FILE_READ_BYTES` (500KB).
- **Returns**:
  ```json
  {
    "file_path": "auth_service/auth.py",
    "total_lines": 105,
    "start_line": 80,
    "end_line": 95,
    "content": "    if payload.get(\"exp\", 0) > current_time:\n        raise TokenExpiredError(\"Token has expired\")\n"
  }
  ```

---

## 4. `search_code`
Performs text search or regular expression matching across repository source files.

- **Parameters**:
  - `query` *(string, required)*: String or regex pattern to search.
  - `file_pattern` *(string, optional)*: Glob filter (e.g., `"*.py"`).
  - `max_results` *(integer, default: `50`)*: Limit matching snippets.
  - `is_regex` *(boolean, default: `false`)*: Whether query is a regex.
- **Returns**:
  ```json
  {
    "query": "TokenExpiredError",
    "total_matches": 2,
    "matches": [
      {
        "file_path": "auth_service/auth.py",
        "line_number": 90,
        "line_content": "raise TokenExpiredError(\"Token has expired\")"
      }
    ]
  }
  ```

---

## 5. `run_tests`
Executes allowlisted test commands inside repository root with strict timeouts and structured failure parsing.

- **Parameters**:
  - `command` *(string, default: `"pytest -v --tb=short"`)*: Allowlisted test command prefix.
  - `test_path` *(string, optional)*: Specific test file or directory.
  - `timeout_seconds` *(integer, default: `20`)*: Subprocess execution timeout.
- **Security Invariant**: Command must begin with an approved allowlist prefix. Shell operators (`;`, `&&`, `|`) are strictly rejected.
- **Returns**:
  ```json
  {
    "command": "pytest -v --tb=short",
    "exit_code": 1,
    "passed": 3,
    "failed": 1,
    "skipped": 0,
    "total": 4,
    "duration_seconds": 0.16,
    "output": "FAILED sample_repo/tests/test_auth.py::test_valid_token_verification...",
    "failures": [
      {
        "test_id": "sample_repo/tests/test_auth.py::test_valid_token_verification",
        "message": "TokenExpiredError: Token has expired"
      }
    ]
  }
  ```

---

## 6. `get_git_status`
Reports branch and working tree state (untracked, modified, and staged files).

- **Parameters**:
  - `repo_path` *(string, optional)*: Path to git repository.
- **Returns**:
  ```json
  {
    "clean": true,
    "branch": "master",
    "untracked": [],
    "modified": [],
    "staged": []
  }
  ```

---

## 7. `get_git_diff`
Inspects git diff for unstaged or staged changes across the repository or a specific target file.

- **Parameters**:
  - `staged` *(boolean, default: `false`)*: Inspect staged changes if true.
  - `file_path` *(string, optional)*: Specific file path to diff.
- **Returns**:
  ```json
  {
    "has_diff": false,
    "diff": "",
    "files_changed": []
  }
  ```

---

## 8. `propose_patch`
Generates a structured unified diff patch proposal and issues a cryptographic approval token.

- **Parameters**:
  - `target_file` *(string, required)*: Relative path to source file.
  - `diff` *(string, required)*: Unified diff proposing the modification.
  - `rationale` *(string, required)*: Technical explanation justifying the change.
- **Governance Invariant**: **Does NOT modify files on disk.** Registers patch in SQLite with status `PENDING_APPROVAL`.
- **Returns**:
  ```json
  {
    "patch_id": "patch_09763067",
    "target_file": "auth_service/auth.py",
    "status": "PENDING_APPROVAL",
    "diff_preview": "--- a/auth_service/auth.py\n+++ b/auth_service/auth.py\n@@ -88,3 +88,3 @@\n-    if payload.get(\"exp\", 0) > current_time:\n+    if payload.get(\"exp\", 0) < current_time:\n",
    "approval_token": "92f759c8e0307223b5d2146e4c703d1544a86b3641ce6bf3c9657b98a0cbe6a8",
    "instructions": "HUMAN APPROVAL REQUIRED: The agent has proposed a fix but CANNOT modify files without explicit authorization."
  }
  ```
