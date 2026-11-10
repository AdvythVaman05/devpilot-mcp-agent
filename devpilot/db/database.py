"""
SQLite Database Layer for DevPilot Execution Trace and Audit History
"""
import json
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from devpilot.config import settings
from devpilot.security import redact_sensitive_data


def now_iso() -> str:
    """Current UTC timestamp in ISO 8601 format."""
    return datetime.now(timezone.utc).isoformat()


class Database:
    """Thread-safe SQLite manager for persisting investigation history."""

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or settings.DATABASE_PATH
        self._local = threading.local()
        self.init_schema()

    def get_connection(self) -> sqlite3.Connection:
        """Returns a thread-local SQLite connection."""
        if not hasattr(self._local, "conn") or self._local.conn is None:
            self._local.conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
            self._local.conn.row_factory = sqlite3.Row
            # Enable WAL mode for high concurrency
            self._local.conn.execute("PRAGMA journal_mode = WAL;")
            self._local.conn.execute("PRAGMA foreign_keys = ON;")
        return self._local.conn

    def init_schema(self) -> None:
        """Initializes tables and indexes."""
        conn = self.get_connection()
        with conn:
            conn.executescript("""
            CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY,
                repository_path TEXT NOT NULL,
                task_description TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS agent_plans (
                id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                steps TEXT NOT NULL,
                current_step_index INTEGER DEFAULT 0,
                created_at TEXT NOT NULL,
                FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS tool_calls (
                id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                tool_name TEXT NOT NULL,
                arguments TEXT NOT NULL,
                result TEXT,
                status TEXT NOT NULL,
                duration_ms INTEGER DEFAULT 0,
                error_message TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS patches (
                id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                target_file TEXT NOT NULL,
                diff TEXT NOT NULL,
                rationale TEXT NOT NULL,
                status TEXT NOT NULL,
                approval_token TEXT NOT NULL,
                created_at TEXT NOT NULL,
                decided_at TEXT,
                decision_reason TEXT,
                FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS test_runs (
                id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                phase TEXT NOT NULL,
                command TEXT NOT NULL,
                exit_code INTEGER NOT NULL,
                passed_count INTEGER DEFAULT 0,
                failed_count INTEGER DEFAULT 0,
                skipped_count INTEGER DEFAULT 0,
                total_count INTEGER DEFAULT 0,
                duration_seconds REAL DEFAULT 0.0,
                raw_output TEXT,
                test_cases TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS reports (
                id TEXT PRIMARY KEY,
                session_id TEXT UNIQUE NOT NULL,
                summary TEXT NOT NULL,
                root_cause TEXT NOT NULL,
                patch_summary TEXT NOT NULL,
                verification_status TEXT NOT NULL,
                full_markdown TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_tool_calls_session ON tool_calls(session_id);
            CREATE INDEX IF NOT EXISTS idx_patches_session ON patches(session_id);
            CREATE INDEX IF NOT EXISTS idx_test_runs_session ON test_runs(session_id);
            """)

    # --- Sessions ---
    def create_session(self, session_id: str, repo_path: str, task: str) -> Dict[str, Any]:
        conn = self.get_connection()
        created = now_iso()
        with conn:
            conn.execute(
                """
                INSERT INTO sessions (id, repository_path, task_description, status, created_at, updated_at)
                VALUES (?, ?, ?, 'INITIALIZING', ?, ?)
                """,
                (session_id, repo_path, task, created, created)
            )
        return self.get_session(session_id)

    def update_session_status(self, session_id: str, status: str) -> None:
        conn = self.get_connection()
        with conn:
            conn.execute(
                "UPDATE sessions SET status = ?, updated_at = ? WHERE id = ?",
                (status, now_iso(), session_id)
            )

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        conn = self.get_connection()
        cur = conn.execute("SELECT * FROM sessions WHERE id = ?", (session_id,))
        row = cur.fetchone()
        return dict(row) if row else None

    def list_sessions(self, limit: int = 50) -> List[Dict[str, Any]]:
        conn = self.get_connection()
        cur = conn.execute("SELECT * FROM sessions ORDER BY created_at DESC LIMIT ?", (limit,))
        return [dict(row) for row in cur.fetchall()]

    # --- Agent Plan ---
    def record_plan(self, plan_id: str, session_id: str, steps: List[Dict[str, Any]], current_step: int = 0) -> None:
        conn = self.get_connection()
        with conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO agent_plans (id, session_id, steps, current_step_index, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (plan_id, session_id, json.dumps(steps), current_step, now_iso())
            )

    def get_plan(self, session_id: str) -> Optional[Dict[str, Any]]:
        conn = self.get_connection()
        cur = conn.execute("SELECT * FROM agent_plans WHERE session_id = ? ORDER BY created_at DESC LIMIT 1", (session_id,))
        row = cur.fetchone()
        if not row:
            return None
        data = dict(row)
        data["steps"] = json.loads(data["steps"])
        return data

    # --- Tool Calls ---
    def record_tool_call(
        self,
        call_id: str,
        session_id: str,
        tool_name: str,
        arguments: Dict[str, Any],
        result: Any,
        status: str,
        duration_ms: int,
        error_message: Optional[str] = None
    ) -> None:
        # Guarantee secret redaction
        clean_args = redact_sensitive_data(arguments)
        clean_result = redact_sensitive_data(result)

        conn = self.get_connection()
        with conn:
            conn.execute(
                """
                INSERT OR IGNORE INTO sessions (id, repository_path, task_description, status, created_at, updated_at)
                VALUES (?, 'system', 'Standalone Tool Call', 'INITIALIZING', ?, ?)
                """,
                (session_id, now_iso(), now_iso())
            )
            conn.execute(
                """
                INSERT INTO tool_calls (id, session_id, tool_name, arguments, result, status, duration_ms, error_message, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    call_id,
                    session_id,
                    tool_name,
                    json.dumps(clean_args),
                    json.dumps(clean_result) if not isinstance(clean_result, str) else clean_result,
                    status,
                    duration_ms,
                    error_message,
                    now_iso(),
                )
            )

    def get_tool_calls(self, session_id: str) -> List[Dict[str, Any]]:
        conn = self.get_connection()
        cur = conn.execute("SELECT * FROM tool_calls WHERE session_id = ? ORDER BY created_at ASC", (session_id,))
        results = []
        for row in cur.fetchall():
            item = dict(row)
            try:
                item["arguments"] = json.loads(item["arguments"])
            except Exception:
                pass
            try:
                item["result"] = json.loads(item["result"])
            except Exception:
                pass
            results.append(item)
        return results

    # --- Patches ---
    def create_patch(
        self,
        patch_id: str,
        session_id: str,
        target_file: str,
        diff: str,
        rationale: str,
        approval_token: str
    ) -> Dict[str, Any]:
        conn = self.get_connection()
        created = now_iso()
        with conn:
            conn.execute(
                """
                INSERT INTO patches (id, session_id, target_file, diff, rationale, status, approval_token, created_at)
                VALUES (?, ?, ?, ?, ?, 'PENDING_APPROVAL', ?, ?)
                """,
                (patch_id, session_id, target_file, diff, rationale, approval_token, created)
            )
        return self.get_patch(patch_id)

    def update_patch_decision(self, patch_id: str, status: str, reason: Optional[str] = None) -> None:
        conn = self.get_connection()
        with conn:
            conn.execute(
                "UPDATE patches SET status = ?, decided_at = ?, decision_reason = ? WHERE id = ?",
                (status, now_iso(), reason, patch_id)
            )

    def get_patch(self, patch_id: str) -> Optional[Dict[str, Any]]:
        conn = self.get_connection()
        cur = conn.execute("SELECT * FROM patches WHERE id = ?", (patch_id,))
        row = cur.fetchone()
        return dict(row) if row else None

    def get_session_patches(self, session_id: str) -> List[Dict[str, Any]]:
        conn = self.get_connection()
        cur = conn.execute("SELECT * FROM patches WHERE session_id = ? ORDER BY created_at DESC", (session_id,))
        return [dict(row) for row in cur.fetchall()]

    # --- Test Runs ---
    def record_test_run(
        self,
        run_id: str,
        session_id: str,
        phase: str,
        command: str,
        exit_code: int,
        passed_count: int,
        failed_count: int,
        skipped_count: int,
        total_count: int,
        duration_seconds: float,
        raw_output: str,
        test_cases: List[Dict[str, Any]]
    ) -> None:
        conn = self.get_connection()
        with conn:
            conn.execute(
                """
                INSERT INTO test_runs (
                    id, session_id, phase, command, exit_code, passed_count,
                    failed_count, skipped_count, total_count, duration_seconds,
                    raw_output, test_cases, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    session_id,
                    phase,
                    command,
                    exit_code,
                    passed_count,
                    failed_count,
                    skipped_count,
                    total_count,
                    duration_seconds,
                    raw_output,
                    json.dumps(test_cases),
                    now_iso(),
                )
            )

    def get_test_runs(self, session_id: str) -> List[Dict[str, Any]]:
        conn = self.get_connection()
        cur = conn.execute("SELECT * FROM test_runs WHERE session_id = ? ORDER BY created_at ASC", (session_id,))
        results = []
        for row in cur.fetchall():
            item = dict(row)
            try:
                item["test_cases"] = json.loads(item["test_cases"])
            except Exception:
                pass
            results.append(item)
        return results

    # --- Reports ---
    def record_report(
        self,
        report_id: str,
        session_id: str,
        summary: str,
        root_cause: str,
        patch_summary: str,
        verification_status: str,
        full_markdown: str
    ) -> None:
        conn = self.get_connection()
        with conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO reports (
                    id, session_id, summary, root_cause, patch_summary,
                    verification_status, full_markdown, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    report_id,
                    session_id,
                    summary,
                    root_cause,
                    patch_summary,
                    verification_status,
                    full_markdown,
                    now_iso(),
                )
            )

    def get_report(self, session_id: str) -> Optional[Dict[str, Any]]:
        conn = self.get_connection()
        cur = conn.execute("SELECT * FROM reports WHERE session_id = ?", (session_id,))
        row = cur.fetchone()
        return dict(row) if row else None


_db_instance: Optional[Database] = None


def get_db() -> Database:
    """Singleton getter for the SQLite database."""
    global _db_instance
    if _db_instance is None:
        _db_instance = Database()
    return _db_instance
