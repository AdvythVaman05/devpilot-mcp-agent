export interface Session {
  id: string;
  repository_path: string;
  task_description: string;
  status: 'INITIALIZING' | 'INVESTIGATING' | 'AWAITING_APPROVAL' | 'PATCH_APPROVED' | 'PATCH_REJECTED' | 'VERIFYING' | 'COMPLETED' | 'FAILED' | 'REJECTED';
  created_at: string;
  updated_at: string;
}

export interface PlanStep {
  id: string;
  description: string;
  status: 'PENDING' | 'IN_PROGRESS' | 'COMPLETED' | 'FAILED';
}

export interface Plan {
  id: string;
  session_id: string;
  steps: PlanStep[];
  current_step_index: number;
}

export interface Stage {
  id: string;
  session_id: string;
  stage_id: number;
  name: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  started_at?: number | null;
  completed_at?: number | null;
  duration_seconds?: number | null;
  explanation: string;
  evidence: string;
}

export interface ExecutionEvent {
  id: string;
  session_id: string;
  category: 'AGENT' | 'MCP' | 'TOOL' | 'TEST' | 'APPROVAL' | 'VERIFICATION' | 'ERROR';
  title: string;
  detail: string;
  data?: any;
  status: 'info' | 'success' | 'warning' | 'error';
  timestamp: string;
}

export interface ToolCall {
  id: string;
  session_id: string;
  tool_name: string;
  arguments: Record<string, any>;
  result: any;
  status: 'SUCCESS' | 'ERROR';
  duration_ms: number;
  error_message?: string | null;
  created_at: string;
}

export interface Patch {
  id: string;
  session_id: string;
  target_file: string;
  diff: string;
  rationale: string;
  status: 'PENDING_APPROVAL' | 'APPROVED' | 'REJECTED' | 'APPLIED';
  approval_token: string;
  created_at: string;
  decided_at?: string | null;
  decision_reason?: string | null;
}

export interface TestFailure {
  test_id: string;
  message: string;
}

export interface TestRun {
  id: string;
  session_id: string;
  phase: 'BASELINE' | 'VERIFICATION';
  command: string;
  exit_code: number;
  passed_count: number;
  failed_count: number;
  skipped_count: number;
  total_count: number;
  duration_seconds: number;
  raw_output?: string;
  test_cases?: TestFailure[];
  created_at: string;
}

export interface Report {
  id: string;
  session_id: string;
  summary: string;
  root_cause: string;
  patch_summary: string;
  verification_status: 'VERIFIED' | 'UNVERIFIED' | 'FAILED_VERIFICATION' | 'REJECTED';
  full_markdown: string;
  created_at: string;
}

export interface SystemHealth {
  status: string;
  app_name: string;
  version: string;
  sample_repo_available: boolean;
  provider_mode?: 'live' | 'demo' | string;
  gemini_api_key_configured: boolean;
  active_provider: string;
  mcp_server_status?: string;
  protocol: string;
}

export interface ApiConfig {
  provider_mode: 'live' | 'demo';
  gemini_model: string;
  gemini_api_key_configured: boolean;
  command_timeout_seconds: number;
  sample_repo_available: boolean;
  protocol: string;
}
