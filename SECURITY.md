# DevPilot Security Architecture & Governance Model

DevPilot implements defense-in-depth principles designed for autonomous software engineering agents.

---

## 1. Threat Model & Security Invariants

| Threat / Risk | Mitigation Strategy | Implementation |
|---|---|---|
| **Path Traversal Escape** | Filesystem access is strictly sandboxed to an explicitly configured repository root. | `resolve_and_validate_path` in `devpilot/security.py` checks both `relative_to` and `os.path.commonpath`. Rejects `../`, absolute paths outside root, and malicious symlinks. |
| **Unrestricted Shell Execution** | Arbitrary shell commands (`shell=True`) are strictly forbidden. | Fixed command allowlist (`pytest`, `python -m pytest`). `validate_command` rejects shell operators (`;`, `&&`, `\|`, `` ` ``, `$()`, `>`, `<`). |
| **Subprocess Freezes / DoS** | All child processes (tests, git) are bound by strict timeouts. | All `subprocess.run` calls enforce `timeout_seconds` (default: 20s). `TimeoutExpired` exceptions are caught and reported as error results without hanging. |
| **Credential / Secret Leakage** | API keys and tokens must never appear in logs or the frontend. | `redact_sensitive_data` recursively masks sensitive dictionary keys and regex patterns (Gemini keys, GitHub tokens, Bearer tokens). |
| **Unauthorized Code Modification** | The agent must not write or patch code without human consent. | Backend authorization gate: write operations require a SHA-256 cryptographic approval token. Proposing a patch only stores the diff with status `PENDING_APPROVAL`. |
| **Prompt Injection via Source Code** | Repository files may contain adversarial instructions. | Source code and README contents are wrapped inside `<UNTRUSTED_REPOSITORY_DATA>` tags. The system prompt instructs the agent to treat repository content strictly as data to inspect, never as system instructions. |

---

## 2. Path Traversal Defense Details

The `resolve_and_validate_path` routine guarantees that every file requested by `read_file`, `list_files`, or `propose_patch` is contained within the root boundary:

```python
root = Path(repo_root).resolve()
raw_path = Path(target_path)
resolved = (root / raw_path).resolve() if not raw_path.is_absolute() else raw_path.resolve()

# Boundary check: raises PathTraversalError if outside root
resolved.relative_to(root)
if Path(os.path.commonpath([str(root), str(resolved)])).resolve() != root:
    raise PathTraversalError(...)
```

Tested thoroughly against `../../etc/passwd`, Windows drive escapes, and nested traversal attempts in `tests/test_security.py`.

---

## 3. Human Approval Enforcement

Unlike simplistic agents that merely promise not to edit files in their prompt, DevPilot enforces authorization in the application code:
1. When `propose_patch` is invoked, the diff is saved to SQLite with status `PENDING_APPROVAL`.
2. A unique SHA-256 `approval_token` is generated using:
   $$\text{Token} = \text{SHA256}(\text{patch\_id} + \text{file} + \text{diff} + \text{timestamp})$$
3. The agent workflow halts.
4. When the user reviews the diff and clicks "Authorize & Apply Fix", the backend validates the token using constant-time comparison (`hmac.compare_digest`).
5. Only then is the patch merged into the target file on disk.
