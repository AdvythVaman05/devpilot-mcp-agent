"""
DevPilot Verification Engine
Executes test suites, captures structured pass/fail metrics,
compares baseline vs post-patch runs, and issues verification verdicts.
"""
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from devpilot.db.database import get_db
from devpilot.mcp_server.models import RunTestsInput, RunTestsOutput
from devpilot.mcp_server.tools import tool_run_tests


class VerificationEngine:
    """
    Executes and compares baseline and post-patch test runs.
    Enforces the invariant: A generated patch is NOT equivalent to a verified fix.
    """

    def __init__(self, db=None):
        self.db = db or get_db()

    def run_suite(
        self,
        session_id: str,
        repo_root: Path,
        phase: str,  # 'BASELINE' or 'VERIFICATION'
        command: str = "pytest -v --tb=short",
        test_path: Optional[str] = None,
    ) -> RunTestsOutput:
        """Executes the test suite and persists the run in SQLite."""
        inp = RunTestsInput(
            command=command,
            test_path=test_path,
        )
        res = tool_run_tests(repo_root, inp)

        run_id = f"run_{phase.lower()}_{uuid.uuid4().hex[:8]}"
        failures_dict = [f.model_dump() for f in res.failures]

        self.db.record_test_run(
            run_id=run_id,
            session_id=session_id,
            phase=phase,
            command=command,
            exit_code=res.exit_code,
            passed_count=res.passed,
            failed_count=res.failed,
            skipped_count=res.skipped,
            total_count=res.total,
            duration_seconds=res.duration_seconds,
            raw_output=res.output,
            test_cases=failures_dict,
        )

        return res

    def compare_runs(
        self,
        baseline: RunTestsOutput,
        verification: RunTestsOutput,
    ) -> Dict[str, Any]:
        """
        Compares baseline failure list against post-patch verification run.
        Determines whether the proposed patch is genuinely VERIFIED.
        """
        baseline_failed_ids = {f.test_id for f in baseline.failures}
        verification_failed_ids = {f.test_id for f in verification.failures}

        # Fixed tests: tests that were in baseline failures but NOT in verification failures
        fixed_tests = list(baseline_failed_ids - verification_failed_ids)
        # Regressions: tests that failed in verification but were NOT in baseline failures
        regressions = list(verification_failed_ids - baseline_failed_ids)
        # Remaining failures
        still_failing = list(baseline_failed_ids.intersection(verification_failed_ids))

        if verification.exit_code == 0 and verification.failed == 0 and len(fixed_tests) > 0:
            status = "VERIFIED"
            summary = (
                f"Fix verified successfully. {len(fixed_tests)} failing test(s) resolved. "
                f"Total suite passing: {verification.passed}/{verification.total}."
            )
        elif verification.failed > 0:
            status = "FAILED_VERIFICATION"
            summary = (
                f"Verification failed. Suite still has {verification.failed} failing test(s). "
                f"Remaining failures: {', '.join(still_failing) if still_failing else 'None'}."
            )
        elif regressions:
            status = "REGRESSION_DETECTED"
            summary = (
                f"Regression detected! New test failure(s) introduced: {', '.join(regressions)}."
            )
        else:
            status = "VERIFIED"
            summary = f"All {verification.passed} test(s) passed successfully."

        return {
            "verification_status": status,
            "summary": summary,
            "baseline": {
                "exit_code": baseline.exit_code,
                "passed": baseline.passed,
                "failed": baseline.failed,
                "total": baseline.total,
            },
            "post_patch": {
                "exit_code": verification.exit_code,
                "passed": verification.passed,
                "failed": verification.failed,
                "total": verification.total,
            },
            "fixed_tests": fixed_tests,
            "regressions": regressions,
            "still_failing": still_failing,
        }


_verification_engine: Optional[VerificationEngine] = None


def get_verification_engine() -> VerificationEngine:
    global _verification_engine
    if _verification_engine is None:
        _verification_engine = VerificationEngine()
    return _verification_engine
