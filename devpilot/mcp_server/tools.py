"""
Implementation of the 8 Core DevPilot MCP Tools
"""
import hashlib
import os
import re
import subprocess
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from devpilot.config import settings
from devpilot.db.database import get_db
from devpilot.mcp_server.models import (
    InspectRepositoryInput,
    InspectRepositoryOutput,
    ListFilesInput,
    ListFilesOutput,
    FileEntry,
    ReadFileInput,
    ReadFileOutput,
    SearchCodeInput,
    SearchCodeOutput,
    SearchMatch,
    RunTestsInput,
    RunTestsOutput,
    TestFailure,
    GetGitStatusInput,
    GetGitStatusOutput,
    GetGitDiffInput,
    GetGitDiffOutput,
    ProposePatchInput,
    ProposePatchOutput,
)
from devpilot.security import (
    resolve_and_validate_path,
    validate_command,
    PathTraversalError,
    DisallowedCommandError,
)

IGNORED_DIRS = {".git", ".venv", "venv", "node_modules", "__pycache__", ".pytest_cache", "dist", "build"}
EXTENSION_LANG_MAP = {
    ".py": "Python",
    ".ts": "TypeScript",
    ".tsx": "React/TypeScript",
    ".js": "JavaScript",
    ".jsx": "React/JavaScript",
    ".json": "JSON",
    ".md": "Markdown",
    ".html": "HTML",
    ".css": "CSS",
    ".sql": "SQL",
    ".yaml": "YAML",
    ".yml": "YAML",
    ".toml": "TOML",
    ".sh": "Shell",
}


def ensure_git_repo(target_dir: Path) -> None:
    """Ensures target directory has a valid git repository initialized."""
    if not (target_dir / ".git").exists():
        try:
            subprocess.run(["git", "init"], cwd=str(target_dir), capture_output=True, timeout=5)
            subprocess.run(["git", "config", "user.name", "DevPilot Bot"], cwd=str(target_dir), capture_output=True, timeout=5)
            subprocess.run(["git", "config", "user.email", "bot@devpilot.internal"], cwd=str(target_dir), capture_output=True, timeout=5)
            subprocess.run(["git", "add", "."], cwd=str(target_dir), capture_output=True, timeout=5)
            subprocess.run(["git", "commit", "-m", "feat(auth): initial authentication service implementation"], cwd=str(target_dir), capture_output=True, timeout=5)
        except Exception:
            pass


def tool_inspect_repository(repo_root: Path, input_data: Optional[InspectRepositoryInput] = None) -> InspectRepositoryOutput:
    """Inspects high-level repository structure, git state, and environment."""
    target_dir = repo_root
    if input_data and input_data.repo_path:
        target_dir = resolve_and_validate_path(input_data.repo_path, repo_root)

    ensure_git_repo(target_dir)
    is_git = (target_dir / ".git").exists()
    branch = None
    head_commit = None

    if is_git:
        try:
            res = subprocess.run(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                cwd=target_dir,
                capture_output=True,
                text=True,
                timeout=5,
            )
            if res.returncode == 0:
                branch = res.stdout.strip()
            
            res_commit = subprocess.run(
                ["git", "rev-parse", "--short", "HEAD"],
                cwd=target_dir,
                capture_output=True,
                text=True,
                timeout=5,
            )
            if res_commit.returncode == 0:
                head_commit = res_commit.stdout.strip()
        except Exception:
            pass

    # Collect files & detect languages
    file_count = 0
    detected_languages = set()
    top_level_entries = []

    for entry in target_dir.iterdir():
        if entry.name in IGNORED_DIRS:
            continue
        top_level_entries.append(entry.name + ("/" if entry.is_dir() else ""))

    for root, dirs, files in os.walk(target_dir):
        # Exclude ignored dirs in-place
        dirs[:] = [d for d in dirs if d not in IGNORED_DIRS]
        for f in files:
            file_count += 1
            ext = Path(f).suffix.lower()
            if ext in EXTENSION_LANG_MAP:
                detected_languages.add(EXTENSION_LANG_MAP[ext])

    # Readme excerpt
    readme_excerpt = None
    readme_candidates = ["README.md", "readme.md", "README.txt", "README"]
    for candidate in readme_candidates:
        candidate_path = target_dir / candidate
        if candidate_path.is_file():
            try:
                with open(candidate_path, "r", encoding="utf-8", errors="replace") as f:
                    readme_excerpt = f.read(1000)
                break
            except Exception:
                pass

    return InspectRepositoryOutput(
        repo_name=target_dir.name,
        root_path=str(target_dir),
        is_git=is_git,
        branch=branch,
        head_commit=head_commit,
        file_count=file_count,
        languages=sorted(list(detected_languages)),
        top_level_entries=sorted(top_level_entries),
        readme_excerpt=readme_excerpt,
    )


def tool_list_files(repo_root: Path, input_data: ListFilesInput) -> ListFilesOutput:
    """Lists files inside the configured repository relative to a directory."""
    target_dir = resolve_and_validate_path(input_data.directory, repo_root)
    if not target_dir.is_dir():
        raise PathTraversalError(f"Target is not a directory: {input_data.directory}")

    files: List[FileEntry] = []
    pattern_regex = None
    if input_data.pattern:
        # Convert simple glob to regex or use fnmatch
        import fnmatch
        pattern = input_data.pattern

    if input_data.recursive:
        for root, dirs, filenames in os.walk(target_dir):
            dirs[:] = [d for d in dirs if d not in IGNORED_DIRS]
            for fname in filenames:
                if len(files) >= input_data.max_results:
                    break
                if input_data.pattern and not fnmatch.fnmatch(fname, input_data.pattern):
                    continue
                file_full = Path(root) / fname
                rel_path = str(file_full.relative_to(repo_root)).replace("\\", "/")
                try:
                    size = file_full.stat().st_size
                except Exception:
                    size = 0
                files.append(FileEntry(
                    path=rel_path,
                    name=fname,
                    is_directory=False,
                    size_bytes=size
                ))
    else:
        import fnmatch
        for entry in target_dir.iterdir():
            if entry.name in IGNORED_DIRS:
                continue
            if len(files) >= input_data.max_results:
                break
            if input_data.pattern and not fnmatch.fnmatch(entry.name, input_data.pattern):
                continue
            rel_path = str(entry.relative_to(repo_root)).replace("\\", "/")
            try:
                size = entry.stat().st_size if entry.is_file() else 0
            except Exception:
                size = 0
            files.append(FileEntry(
                path=rel_path,
                name=entry.name,
                is_directory=entry.is_dir(),
                size_bytes=size
            ))

    return ListFilesOutput(
        base_directory=input_data.directory,
        files=files,
        total_count=len(files),
    )


def tool_read_file(repo_root: Path, input_data: ReadFileInput) -> ReadFileOutput:
    """Reads lines from an allowlisted file inside the repository."""
    file_path = resolve_and_validate_path(input_data.file_path, repo_root)
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: '{input_data.file_path}'")
    if file_path.is_dir():
        raise IsADirectoryError(f"Path is a directory, not a file: '{input_data.file_path}'")

    stat = file_path.stat()
    if stat.st_size > settings.MAX_FILE_READ_BYTES:
        raise ValueError(
            f"File size {stat.st_size} bytes exceeds maximum allowed read limit ({settings.MAX_FILE_READ_BYTES} bytes)"
        )

    with open(file_path, "r", encoding="utf-8", errors="replace") as f:
        lines = f.readlines()

    total_lines = len(lines)
    start_line = max(1, input_data.start_line or 1)
    end_line = min(total_lines, input_data.end_line or total_lines)

    if start_line > total_lines:
        content_slice = ""
    else:
        # 1-indexed to 0-indexed slice
        content_slice = "".join(lines[start_line - 1 : end_line])

    rel_path = str(file_path.relative_to(repo_root)).replace("\\", "/")
    return ReadFileOutput(
        file_path=rel_path,
        total_lines=total_lines,
        start_line=start_line,
        end_line=end_line,
        content=content_slice,
    )


def tool_search_code(repo_root: Path, input_data: SearchCodeInput) -> SearchCodeOutput:
    """Searches for text or regex across text files in the repository."""
    matches: List[SearchMatch] = []
    import fnmatch

    if input_data.is_regex:
        try:
            pattern = re.compile(input_data.query, re.IGNORECASE)
        except re.error as e:
            raise ValueError(f"Invalid regex query: {str(e)}")
    else:
        query_lower = input_data.query.lower()

    for root, dirs, files in os.walk(repo_root):
        dirs[:] = [d for d in dirs if d not in IGNORED_DIRS]
        for fname in files:
            if len(matches) >= input_data.max_results:
                break
            if input_data.file_pattern and not fnmatch.fnmatch(fname, input_data.file_pattern):
                continue

            file_full = Path(root) / fname
            # Only inspect text extensions
            if file_full.suffix.lower() not in EXTENSION_LANG_MAP and not fname.endswith(".txt"):
                continue

            try:
                rel_path = str(file_full.relative_to(repo_root)).replace("\\", "/")
                with open(file_full, "r", encoding="utf-8", errors="ignore") as f:
                    for line_idx, line in enumerate(f, start=1):
                        matched = False
                        if input_data.is_regex:
                            matched = bool(pattern.search(line))
                        else:
                            matched = query_lower in line.lower()

                        if matched:
                            matches.append(SearchMatch(
                                file_path=rel_path,
                                line_number=line_idx,
                                line_content=line.strip()[:200],
                            ))
                            if len(matches) >= input_data.max_results:
                                break
            except Exception:
                continue

    return SearchCodeOutput(
        query=input_data.query,
        matches=matches,
        total_matches=len(matches),
    )


def _parse_pytest_output(output_text: str) -> tuple[int, int, int, int, List[TestFailure]]:
    """Parses pytest summary line and failure tracebacks."""
    passed = 0
    failed = 0
    skipped = 0
    total = 0
    failures: List[TestFailure] = []

    # Parse summary like '1 failed, 3 passed in 0.16s' or '4 passed in 0.12s'
    summary_match = re.search(r'=+\s*(.*?)\s+in\s+[\d\.]+s\s*=+', output_text)
    if summary_match:
        summary = summary_match.group(1)
        passed_m = re.search(r'(\d+)\s+passed', summary)
        failed_m = re.search(r'(\d+)\s+failed', summary)
        skipped_m = re.search(r'(\d+)\s+skipped', summary)

        if passed_m:
            passed = int(passed_m.group(1))
        if failed_m:
            failed = int(failed_m.group(1))
        if skipped_m:
            skipped = int(skipped_m.group(1))
        total = passed + failed + skipped

    # Parse failure details
    # Look for 'FAILED path/to/file.py::test_name - ErrorMessage'
    fail_matches = re.finditer(r'FAILED\s+([^\s]+)\s*-\s*([^\r\n]+)', output_text)
    for fm in fail_matches:
        failures.append(TestFailure(test_id=fm.group(1), message=fm.group(2).strip()))

    if not failures and failed > 0:
        # Fallback regex for pytest failure headers: '___ test_name ___'
        header_matches = re.finditer(r'___\s+([a-zA-Z0-9_]+)\s+___', output_text)
        for hm in header_matches:
            failures.append(TestFailure(test_id=hm.group(1), message="Assertion or test failure"))

    return passed, failed, skipped, total, failures


def tool_run_tests(repo_root: Path, input_data: RunTestsInput) -> RunTestsOutput:
    """Executes allowlisted test suite inside repo_root with strict timeouts and error capture."""
    command_str = input_data.command

    # If specific test_path provided, append it safely
    if input_data.test_path:
        test_file = resolve_and_validate_path(input_data.test_path, repo_root)
        rel_test_file = str(test_file.relative_to(repo_root)).replace("\\", "/")
        command_str = f"{command_str} {rel_test_file}"

    # Validate against command allowlist
    cmd_tokens = validate_command(command_str)

    # Use current virtualenv python if command starts with python or pytest
    import sys
    venv_python = sys.executable
    if cmd_tokens[0] == "python":
        cmd_tokens[0] = venv_python
    elif cmd_tokens[0] == "pytest":
        cmd_tokens = [venv_python, "-m", "pytest"] + cmd_tokens[1:]

    timeout = input_data.timeout_seconds or settings.COMMAND_TIMEOUT_SECONDS
    start_time = time.time()

    # Pass PYTHONPATH to ensure repo modules are importable
    env = os.environ.copy()
    env["PYTHONPATH"] = f"{str(repo_root)}{os.pathsep}{env.get('PYTHONPATH', '')}"

    try:
        proc = subprocess.run(
            cmd_tokens,
            cwd=str(repo_root),
            capture_output=True,
            text=True,
            timeout=timeout,
            env=env,
        )
        duration = round(time.time() - start_time, 3)
        combined_output = proc.stdout + ("\n" + proc.stderr if proc.stderr else "")
        passed, failed, skipped, total, failures = _parse_pytest_output(combined_output)

        return RunTestsOutput(
            command=command_str,
            exit_code=proc.returncode,
            passed=passed,
            failed=failed,
            skipped=skipped,
            total=total,
            duration_seconds=duration,
            output=combined_output,
            failures=failures,
        )

    except subprocess.TimeoutExpired as te:
        duration = round(time.time() - start_time, 3)
        err_msg = f"Test execution timed out after {timeout} seconds."
        return RunTestsOutput(
            command=command_str,
            exit_code=-1,
            passed=0,
            failed=1,
            skipped=0,
            total=1,
            duration_seconds=duration,
            output=err_msg,
            failures=[TestFailure(test_id="timeout", message=err_msg)],
        )
    except Exception as e:
        duration = round(time.time() - start_time, 3)
        return RunTestsOutput(
            command=command_str,
            exit_code=1,
            passed=0,
            failed=1,
            skipped=0,
            total=1,
            duration_seconds=duration,
            output=str(e),
            failures=[TestFailure(test_id="execution_error", message=str(e))],
        )


def tool_get_git_status(repo_root: Path, input_data: Optional[GetGitStatusInput] = None) -> GetGitStatusOutput:
    """Inspects git status (untracked, modified, staged files)."""
    target_dir = repo_root
    if input_data and input_data.repo_path:
        target_dir = resolve_and_validate_path(input_data.repo_path, repo_root)

    if not (target_dir / ".git").exists():
        return GetGitStatusOutput(
            clean=True,
            branch="non-git",
            untracked=[],
            modified=[],
            staged=[],
        )

    try:
        res = subprocess.run(
            ["git", "status", "--porcelain=v1", "-b"],
            cwd=str(target_dir),
            capture_output=True,
            text=True,
            timeout=5,
        )
        lines = res.stdout.splitlines()
        branch = "unknown"
        untracked = []
        modified = []
        staged = []

        for line in lines:
            if line.startswith("## "):
                branch = line[3:].split("...")[0].strip()
            elif line.startswith("?? "):
                untracked.append(line[3:].strip())
            elif line.startswith(" M ") or line.startswith("AM "):
                modified.append(line[3:].strip())
            elif line.startswith("M  ") or line.startswith("A  "):
                staged.append(line[3:].strip())

        clean = len(untracked) == 0 and len(modified) == 0 and len(staged) == 0

        return GetGitStatusOutput(
            clean=clean,
            branch=branch,
            untracked=untracked,
            modified=modified,
            staged=staged,
        )
    except Exception as e:
        return GetGitStatusOutput(
            clean=True,
            branch="error",
            untracked=[],
            modified=[],
            staged=[],
        )


def tool_get_git_diff(repo_root: Path, input_data: GetGitDiffInput) -> GetGitDiffOutput:
    """Inspects git diff for pending changes."""
    cmd = ["git", "diff"]
    if input_data.staged:
        cmd.append("--cached")
    if input_data.file_path:
        rel_file = resolve_and_validate_path(input_data.file_path, repo_root)
        cmd.append(str(rel_file.relative_to(repo_root)))

    try:
        res = subprocess.run(
            cmd,
            cwd=str(repo_root),
            capture_output=True,
            text=True,
            timeout=5,
        )
        diff_text = res.stdout
        files_changed = []
        for line in diff_text.splitlines():
            if line.startswith("+++ b/"):
                files_changed.append(line[6:].strip())

        return GetGitDiffOutput(
            has_diff=bool(diff_text.strip()),
            diff=diff_text,
            files_changed=files_changed,
        )
    except Exception as e:
        return GetGitDiffOutput(
            has_diff=False,
            diff="",
            files_changed=[],
        )


def tool_propose_patch(repo_root: Path, input_data: ProposePatchInput, session_id: Optional[str] = None) -> ProposePatchOutput:
    """
    Proposes a code patch without applying it.
    Generates a secure approval token and registers the patch in PENDING_APPROVAL status.
    Strictly forbids modifying source files until human approval is authorized.
    """
    target = resolve_and_validate_path(input_data.target_file, repo_root)
    rel_path = str(target.relative_to(repo_root)).replace("\\", "/")

    patch_id = f"patch_{uuid.uuid4().hex[:8]}"
    token_seed = f"{patch_id}:{rel_path}:{input_data.diff}:{time.time()}"
    approval_token = hashlib.sha256(token_seed.encode("utf-8")).hexdigest()

    # Persist in DB if session is active
    if session_id:
        db = get_db()
        db.create_patch(
            patch_id=patch_id,
            session_id=session_id,
            target_file=rel_path,
            diff=input_data.diff,
            rationale=input_data.rationale,
            approval_token=approval_token,
        )

    instructions = (
        "HUMAN APPROVAL REQUIRED: The agent has proposed a fix but CANNOT modify files "
        "without explicit authorization. Present the diff preview and rationale to the user. "
        "The user must approve the patch via the UI or POST /api/sessions/{session_id}/patches/{patch_id}/approve."
    )

    return ProposePatchOutput(
        patch_id=patch_id,
        target_file=rel_path,
        rationale=input_data.rationale,
        status="PENDING_APPROVAL",
        diff_preview=input_data.diff,
        approval_token=approval_token,
        instructions=instructions,
    )
