export type RuntimeState = "stopped" | "starting" | "running" | "paused" | "error";
export type ComputerStatus = "sleeping" | "online";

export interface Computer {
  id: string;
  user_id: string;
  status: ComputerStatus;
  runtime_state: RuntimeState;
  sandbox_id: string | null;
  snapshot_id: string | null;
  workspace_path: string;
  desktop_host: string | null;
  desktop_port: number | null;
  desktop_url: string | null;
  last_booted_at: string | null;
  last_paused_at: string | null;
  last_snapshot_at: string | null;
  error_message: string | null;
  last_active: string;
  created_at: string;
  updated_at: string;
}

export interface Session {
  id: string;
  user_id: string;
  computer_id: string;
  title: string;
  created_at: string;
  updated_at: string;
}

export interface Message {
  id: string;
  session_id: string;
  user_id: string;
  role: "user" | "assistant";
  content: string;
  model: string | null;
  citations: unknown[] | null;
  created_at: string;
}

export type SSEEventType =
  | "ready"
  | "status"
  | "tool_call"
  | "text_delta"
  | "final"
  | "error"
  | "_keepalive";

export interface SSEEvent {
  type: SSEEventType;
  text?: string;
  content?: string;
  id?: string;
  user_id?: string;
  model?: string;
  citations?: unknown[];
  created_at?: string;
}
