import json
import os
import sys
import time
import requests

BASE = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("DEVPILOT_API_URL", "http://127.0.0.1:8000/api")


print("--- 1. Health Check ---")
res = requests.get(f"{BASE}/health")
assert res.status_code == 200
print(json.dumps(res.json(), indent=2))

print("\n--- 2. Reset Sample Repository to Baseline ---")
reset_res = requests.post(f"{BASE}/demo/reset")
print("Reset response:", reset_res.json())

print("\n--- 3. Create Investigation Session ---")
sess_res = requests.post(
    f"{BASE}/sessions",
    json={"task": "Investigate why authentication tests fail, identify root cause, and propose fix."}
)
session_data = sess_res.json()
sid = session_data["session_id"]
print(f"Created Session ID: {sid}")

print("\n--- 4. Start Autonomous MCP Investigation ---")
inv_res = requests.post(
    f"{BASE}/sessions/{sid}/investigate",
    json={"provider_mode": "demo"}
)
print("Investigate trigger response:", inv_res.json())

print("\n--- 5. Monitoring Multi-Turn Agent Loop & MCP Tool Execution ---")
patch = None
for i in range(25):
    time.sleep(1)
    details = requests.get(f"{BASE}/sessions/{sid}").json()
    status = details["session"]["status"]
    tool_count = len(details.get("tool_calls", []))
    stage_count = len(details.get("stages", []))
    event_count = len(details.get("events", []))
    print(f"[{i+1}s] Status: {status} | Tools Invoked: {tool_count} | Stages Recorded: {stage_count} | Events: {event_count}")

    if details.get("tool_calls"):
        latest_tool = details["tool_calls"][-1]
        print(f"     -> Latest Tool: {latest_tool['tool_name']} (duration: {latest_tool['duration_ms']}ms)")

    if status == "AWAITING_APPROVAL":
        print("\n=== Agent Halted at Stage 8: AWAITING_APPROVAL ===")
        patch = details["patches"][0]
        break

assert patch is not None, "Agent did not produce a patch awaiting approval"
print(f"Patch ID: {patch['id']}")
print(f"Target File: {patch['target_file']}")
print(f"Approval Token (SHA-256): {patch['approval_token']}")
print(f"Rationale: {patch['rationale']}")
print("Diff Preview:\n" + patch["diff"])

print("\n--- 6. Authorize & Apply Patch via Backend Approval Engine ---")
appr_res = requests.post(
    f"{BASE}/sessions/{sid}/patches/{patch['id']}/approve",
    json={"approval_token": patch["approval_token"]}
)
appr_data = appr_res.json()
print("Approve response status:", appr_data.get("status"))
print("Verification summary:", appr_data.get("verification", {}).get("summary"))
print("Fixed tests:", appr_data.get("verification", {}).get("fixed_tests"))
print("Regressions:", appr_data.get("verification", {}).get("regressions"))

print("\n--- 7. Final Session Audit & Engineering Report ---")
final = requests.get(f"{BASE}/sessions/{sid}").json()
print("Session Final Status:", final["session"]["status"])
print(f"Total MCP Tools Invoked: {len(final['tool_calls'])}")
for tc in final["tool_calls"]:
    print(f" - Tool: {tc['tool_name']:<15} Status: {tc['status']:<8} Duration: {tc['duration_ms']}ms")

print("\n10 Stages Summary:")
for st in final.get("stages", []):
    print(f" - Stage {st['stage_id']:<2}: {st['name']:<45} Status: {st['status']:<10} Duration: {st.get('duration_seconds')}s")

print("\nEngineering Report Excerpt:")
rep = final.get("report")
if rep:
    print(f"Root Cause: {rep['root_cause']}")
    print(f"Verification: {rep['verification_status']}")
    print("Report Markdown lines: " + str(len(rep["full_markdown"].splitlines())))
