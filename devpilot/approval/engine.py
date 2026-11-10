"""
DevPilot Human Approval System
Enforces backend authorization logic for write operations.
Source files cannot be modified until explicit human approval is validated.
"""
import hmac
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Dict, Optional

from devpilot.config import settings
from devpilot.db.database import get_db
from devpilot.security import (
    resolve_and_validate_path,
    UnauthorizedWriteError,
    SecurityError,
)


class ApprovalEngine:
    """
    Manages patch approval tokens, authorization state machines,
    and secure write operations.
    """

    def __init__(self, db=None):
        self.db = db or get_db()

    def approve_and_apply(
        self,
        patch_id: str,
        approval_token: str,
        repo_root: Path,
    ) -> Dict[str, Any]:
        """
        Validates authorization token and applies approved patch to filesystem.
        Strictly rejects unauthorized or tampered patch requests.
        """
        patch = self.db.get_patch(patch_id)
        if not patch:
            raise UnauthorizedWriteError(f"Patch '{patch_id}' not found.")

        # Status check
        if patch["status"] != "PENDING_APPROVAL":
            raise UnauthorizedWriteError(
                f"Patch '{patch_id}' is in status '{patch["status"]}'. "
                "Only patches in 'PENDING_APPROVAL' state may be approved and applied."
            )

        # Cryptographic constant-time token comparison
        stored_token = patch["approval_token"]
        if not hmac.compare_digest(stored_token, approval_token):
            raise UnauthorizedWriteError(
                f"Invalid approval token for patch '{patch_id}'. Authorization denied."
            )

        # Target file security validation
        target_file = resolve_and_validate_path(patch["target_file"], repo_root)
        if not target_file.exists():
            raise FileNotFoundError(f"Target file for patch not found: {patch['target_file']}")

        # Apply the patch
        diff_text = patch["diff"]
        apply_success = False
        apply_method = "git"

        # Try git apply first if repo is a git repo
        if (repo_root / ".git").exists():
            with tempfile.NamedTemporaryFile("w", suffix=".patch", delete=False, encoding="utf-8") as tmp:
                tmp.write(diff_text)
                tmp_path = tmp.name

            try:
                # git apply
                res = subprocess.run(
                    ["git", "apply", "--ignore-whitespace", "--unidiff-zero", tmp_path],
                    cwd=str(repo_root),
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                if res.returncode == 0:
                    apply_success = True
            except Exception:
                pass
            finally:
                if os.path.exists(tmp_path):
                    os.unlink(tmp_path)

        # Fallback python hunk / replacement logic if git apply didn't succeed
        if not apply_success:
            apply_method = "direct_hunk_replacement"
            apply_success = self._apply_diff_python_fallback(target_file, diff_text)

        if not apply_success:
            raise SecurityError(
                f"Failed to apply patch to '{patch['target_file']}'. Diff could not be cleanly merged."
            )

        # Transition patch state to APPLIED
        self.db.update_patch_decision(patch_id, status="APPLIED", reason="Approved and applied by user")
        self.db.update_session_status(patch["session_id"], status="PATCH_APPROVED")

        return {
            "patch_id": patch_id,
            "session_id": patch["session_id"],
            "status": "APPLIED",
            "target_file": str(target_file.relative_to(repo_root)).replace("\\", "/"),
            "apply_method": apply_method,
            "message": "Patch authorized and successfully applied to source file.",
        }

    def reject_patch(
        self,
        patch_id: str,
        reason: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Rejects a proposed patch and marks it as REJECTED without modifying files."""
        patch = self.db.get_patch(patch_id)
        if not patch:
            raise UnauthorizedWriteError(f"Patch '{patch_id}' not found.")

        if patch["status"] != "PENDING_APPROVAL":
            raise UnauthorizedWriteError(
                f"Patch '{patch_id}' is in status '{patch['status']}' and cannot be rejected."
            )

        rejection_reason = reason or "Rejected by human reviewer"
        self.db.update_patch_decision(patch_id, status="REJECTED", reason=rejection_reason)
        self.db.update_session_status(patch["session_id"], status="PATCH_REJECTED")

        return {
            "patch_id": patch_id,
            "session_id": patch["session_id"],
            "status": "REJECTED",
            "reason": rejection_reason,
            "message": "Patch rejected. No source files were modified.",
        }

    def _apply_diff_python_fallback(self, target_path: Path, diff_text: str) -> bool:
        """
        Extracts '-' lines (removal) and '+' lines (addition) from diff
        and performs clean string substitution on the target file.
        """
        try:
            with open(target_path, "r", encoding="utf-8") as f:
                content = f.read()

            removed_lines = []
            added_lines = []

            for line in diff_text.splitlines():
                if line.startswith("---") or line.startswith("+++") or line.startswith("@@"):
                    continue
                if line.startswith("-"):
                    removed_lines.append(line[1:])
                elif line.startswith("+"):
                    added_lines.append(line[1:])

            old_chunk = "\n".join(removed_lines).strip()
            new_chunk = "\n".join(added_lines).strip()

            if old_chunk and old_chunk in content:
                patched_content = content.replace(old_chunk, new_chunk, 1)
                with open(target_path, "w", encoding="utf-8") as f:
                    f.write(patched_content)
                return True

            # Line by line replacement if single line changed
            if len(removed_lines) == 1 and len(added_lines) == 1:
                r_line = removed_lines[0].strip()
                a_line = added_lines[0].strip()
                if r_line in content:
                    patched_content = content.replace(r_line, a_line, 1)
                    with open(target_path, "w", encoding="utf-8") as f:
                        f.write(patched_content)
                    return True

            return False
        except Exception:
            return False


_approval_engine: Optional[ApprovalEngine] = None


def get_approval_engine() -> ApprovalEngine:
    global _approval_engine
    if _approval_engine is None:
        _approval_engine = ApprovalEngine()
    return _approval_engine
