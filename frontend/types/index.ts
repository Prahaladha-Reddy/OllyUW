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

export type MessagePart =
  | { type: "text"; text: string }
  | { type: "tool_call"; id: string; tool: string; args: Record<string, unknown> }
  | { type: "tool_result"; id: string; tool: string; ok: boolean; output: string | null };

export interface Message {
  id: string;
  session_id: string;
  user_id: string;
  role: "user" | "assistant";
  content: string;
  model: string | null;
  citations: unknown[] | null;
  parts: MessagePart[] | null;
  created_at: string;
}

export type SSEEventType =
  | "ready"
  | "status"
  | "tool_call"
  | "tool_result"
  | "text_delta"
  | "final"
  | "error"
  | "_keepalive"
  | "subagent_start"
  | "subagent_done";

export interface SSEEvent {
  type: SSEEventType;
  text?: string;
  content?: string;
  id?: string;
  user_id?: string;
  model?: string;
  citations?: unknown[];
  created_at?: string;
  tool?: string;
  args?: Record<string, unknown>;
  ok?: boolean;
  output?: string;
  // Subagent fields — present on tool_call/tool_result and subagent_start/done events
  subagent_id?: string;
  subagent_label?: string;
  goal?: string;
  toolsets?: string[];
  success?: boolean;
  summary?: string;
}

export type LiveItem =
  | { kind: "text"; id: string; text: string }
  | {
      kind: "tool";
      id: string;
      tool: string;
      args: Record<string, unknown>;
      status: "running" | "done" | "error";
      output?: string;
    };
