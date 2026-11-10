"""
Deterministic Mock Gemini Provider for Automated Testing and Offline Demos
Faithfully simulates Gemini function calling and reasoning steps without requiring external API credentials.
"""
from typing import Any, Dict, List, Optional


class MockToolCall:
    def __init__(self, name: str, args: Dict[str, Any]):
        self.name = name
        self.args = args


class MockCandidate:
    def __init__(self, text: Optional[str] = None, function_calls: Optional[List[MockToolCall]] = None):
        self.text = text
        self.function_calls = function_calls or []


class MockGeminiResponse:
    def __init__(self, candidates: List[MockCandidate]):
        self.candidates = candidates

    @property
    def text(self) -> Optional[str]:
        if self.candidates and self.candidates[0].text:
            return self.candidates[0].text
        return None

    @property
    def function_calls(self) -> List[MockToolCall]:
        if self.candidates:
            return self.candidates[0].function_calls
        return []


class MockGeminiProvider:
    """
    Simulates multi-turn reasoning and tool invocation for investigating
    the authentication service test failure.
    """

    def __init__(self):
        self.turn = 0
        self.history: List[Dict[str, Any]] = []

    def generate_next_step(self, tool_history: List[Dict[str, Any]]) -> MockGeminiResponse:
        """
        Determines the next agent action based on prior MCP tool calls and results.
        """
        self.turn += 1

        # Check if run_tests has been executed
        test_calls = [c for c in tool_history if c["tool_name"] == "run_tests"]
        search_calls = [c for c in tool_history if c["tool_name"] == "search_code"]
        read_calls = [c for c in tool_history if c["tool_name"] == "read_file"]
        patch_calls = [c for c in tool_history if c["tool_name"] == "propose_patch"]

        # Step 1: No tests run yet -> Call run_tests to establish baseline
        if not test_calls:
            return MockGeminiResponse([
                MockCandidate(
                    text="Establishing baseline by executing test suite...",
                    function_calls=[
                        MockToolCall("run_tests", {"command": "pytest -v --tb=short"})
                    ]
                )
            ])

        last_test = test_calls[-1]["result"]
        # If tests failed and search not yet run -> Search for the failing symbol
        if last_test.get("failed", 0) > 0 and not search_calls:
            return MockGeminiResponse([
                MockCandidate(
                    text="Baseline test failure observed in `test_valid_token_verification`. Searching codebase for TokenExpiredError...",
                    function_calls=[
                        MockToolCall("search_code", {"query": "TokenExpiredError", "file_pattern": "*.py"})
                    ]
                )
            ])

        # Step 3: Search done -> Read the failing source file auth.py
        if search_calls and not read_calls:
            return MockGeminiResponse([
                MockCandidate(
                    text="TokenExpiredError located in auth_service/auth.py. Inspecting implementation...",
                    function_calls=[
                        MockToolCall("read_file", {"file_path": "auth_service/auth.py", "start_line": 70, "end_line": 105})
                    ]
                )
            ])

        # Step 4: File read -> Propose patch
        if read_calls and not patch_calls:
            diff = (
                "--- a/auth_service/auth.py\n"
                "+++ b/auth_service/auth.py\n"
                "@@ -88,3 +88,3 @@\n"
                "-    if payload.get(\"exp\", 0) > current_time:\n"
                "+    if payload.get(\"exp\", 0) < current_time:\n"
            )
            rationale = (
                "The token verification routine had an inverted comparison operator in the expiration check. "
                "It checked `payload['exp'] > current_time`, causing freshly issued, valid tokens with future "
                "expiration timestamps to be rejected immediately with TokenExpiredError. Inverting the condition "
                "to `payload['exp'] < current_time` correctly permits unexpired tokens and rejects genuinely expired ones."
            )
            return MockGeminiResponse([
                MockCandidate(
                    text="Root cause identified: Inverted comparison operator in token expiration check. Proposing patch for human approval.",
                    function_calls=[
                        MockToolCall("propose_patch", {
                            "target_file": "auth_service/auth.py",
                            "diff": diff,
                            "rationale": rationale,
                        })
                    ]
                )
            ])

        # Step 5: After patch and verification -> Final summary
        return MockGeminiResponse([
            MockCandidate(
                text=(
                    "Investigation and patch proposal completed. "
                    "The agent identified the inverted comparison operator `>` on line 88 of `auth_service/auth.py`. "
                    "The patch has been proposed and stored with status PENDING_APPROVAL. "
                    "Awaiting explicit user authorization before applying changes to the filesystem."
                )
            )
        ])
