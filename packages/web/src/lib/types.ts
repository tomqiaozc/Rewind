// Session list item (from SessionListItem schema)
export interface SessionListItem {
  id: string;
  session_key: string;
  source: string; // "claude_code" | "opencode" | "gemini_cli" | "codex" | "vscode_copilot"
  started_at: string;
  last_message_at: string | null;
  duration_seconds: number | null;
  total_messages: number;
  user_messages: number;
  assistant_messages: number;
  total_input_tokens: number;
  total_output_tokens: number;
  project_name: string | null;
  model: string | null;
  title: string | null;
  is_starred: boolean;
  created_at: string;
  tags: TagSummary[];
}

// Session list response (paginated)
export interface SessionListResponse {
  items: SessionListItem[];
  total: number;
  page: number;
  page_size: number;
  has_more: boolean;
}

// Message detail for session replay
export interface MessageDetail {
  id: string;
  role: string; // "user" | "assistant" | "tool" | "system"
  ordinal: number;
  tool_name: string | null;
  tool_call_id: string | null;
  tool_status: string | null;
  input_tokens: number;
  output_tokens: number;
  started_at: string | null;
  ended_at: string | null;
  content: string;
}

// Session detail (full session with messages)
export interface SessionDetail {
  id: string;
  session_key: string;
  source: string;
  started_at: string;
  last_message_at: string | null;
  duration_seconds: number | null;
  total_messages: number;
  user_messages: number;
  assistant_messages: number;
  total_input_tokens: number;
  total_output_tokens: number;
  project_name: string | null;
  model: string | null;
  title: string | null;
  is_starred: boolean;
  created_at: string;
  summary: string | null;
  content_key: string | null;
  content_size: number | null;
  raw_key: string | null;
  raw_size: number | null;
  content_hash: string | null;
  raw_hash: string | null;
  parser_revision: number;
  schema_version: number;
  ingested_at: string | null;
  messages: MessageDetail[];
  tags: TagSummary[];
}

// Tag summary
export interface TagSummary {
  id: string;
  name: string;
  color: string;
}

// Filter values for dropdowns
export interface FilterValues {
  sources: string[];
  projects: string[];
  models: string[];
}

// Search result
export interface SearchResult {
  session_id: string;
  session_title: string | null;
  source: string;
  started_at: string;
  message_id: string;
  ordinal: number;
  snippet: string; // HTML with <mark> tags
  role: string;
}

// Search response
export interface SearchResponse {
  results: SearchResult[];
  total: number;
  query: string;
}

// Dashboard stats
export interface DayCount {
  date: string;
  count: number;
}

export interface DashboardStats {
  total_sessions: number;
  total_messages: number;
  total_input_tokens: number;
  total_output_tokens: number;
  sessions_by_source: Record<string, number>;
  sessions_by_day: DayCount[];
  recent_sessions: SessionListItem[];
}

// Tag (full, for settings page)
export interface Tag {
  id: string;
  name: string;
  color: string;
  created_at: string | null;
  session_count: number;
}

// Project summary
export interface ProjectSummary {
  project_name: string;
  session_count: number;
  total_messages: number;
  total_input_tokens: number;
  total_output_tokens: number;
  total_duration_seconds: number;
  last_session_at: string | null;
  sources: string[];
}

// Project activity
export interface ProjectActivity {
  date: string;
  project_name: string;
  count: number;
}

// Batch operations
export interface BatchRequest {
  session_ids: string[];
  action: "star" | "unstar" | "trash" | "restore";
}

export interface BatchResponse {
  affected: number;
}

// API Key
export interface ApiKey {
  id: string;
  device_name: string | null;
  key_prefix: string | null;
  created_at: string;
  last_used_at: string | null;
}

// Source type display helpers
export const SOURCE_LABELS: Record<string, string> = {
  claude_code: "Claude Code",
  opencode: "OpenCode",
  gemini_cli: "Gemini CLI",
  codex: "Codex",
  vscode_copilot: "VS Code Copilot",
};

export const SOURCE_COLORS: Record<string, string> = {
  claude_code: "hsl(24, 95%, 53%)",    // orange
  opencode: "hsl(262, 83%, 58%)",       // purple
  gemini_cli: "hsl(210, 100%, 56%)",    // blue
  codex: "hsl(142, 71%, 45%)",          // green
  vscode_copilot: "hsl(200, 98%, 39%)", // teal
};
