import { getAccessToken } from "./supabase";
import type { Computer, Session, Message, SSEEvent } from "@/types";

const BASE = process.env["NEXT_PUBLIC_API_URL"] ?? "http://localhost:8000";

// Core fetch wrapper — injects the Supabase JWT as Bearer.
async function apiFetch<T>(path: string, init: RequestInit = {}): Promise<T> {
  const token = await getAccessToken();
  if (!token) throw new ApiError(401, "Not authenticated");

  const res = await fetch(`${BASE}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
      ...(init.headers ?? {}),
    },
  });

  if (!res.ok) {
    let detail = `HTTP ${res.status}`;
    try {
      const body = await res.json();
      detail = body.detail ?? detail;
    } catch {}
    throw new ApiError(res.status, detail);
  }

  return res.json() as Promise<T>;
}

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

// ---- Computer ----

export const computerApi = {
  get: () => apiFetch<{ computer: Computer }>("/computer"),
  start: () => apiFetch<{ computer: Computer }>("/computer/runtime/start", { method: "POST" }),
  connect: () => apiFetch<{ computer: Computer }>("/computer/runtime/connect", { method: "POST" }),
  keepalive: () => apiFetch<{ ok: boolean; reason?: string }>("/computer/runtime/keepalive", { method: "POST" }),
  pause: () => apiFetch<{ computer: Computer }>("/computer/runtime/pause", { method: "POST" }),
  powerOff: () => apiFetch<{ computer: Computer }>("/computer/runtime/power-off", { method: "POST" }),
  snapshot: () => apiFetch<{ computer: Computer }>("/computer/runtime/snapshot", { method: "POST" }),
  reset: () => apiFetch<{ computer: Computer }>("/computer/runtime/reset", { method: "POST" }),
  applyMacLook: () => apiFetch<{ output: string }>("/computer/desktop/mac-look", { method: "POST" }),

  workspace: {
    listFolders: () => apiFetch<{ folders: string[] }>("/computer/workspace/folders"),
    listFiles: () => apiFetch<{ files: string[] }>("/computer/workspace"),

    upload: async (files: File[], destPath: string): Promise<{ written: string[] }> => {
      const token = await getAccessToken();
      if (!token) throw new ApiError(401, "Not authenticated");

      const form = new FormData();
      files.forEach((f) => form.append("files", f));
      form.append("path", destPath);

      const res = await fetch(`${BASE}/computer/workspace/upload`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
        body: form,
      });

      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new ApiError(res.status, body.detail ?? `HTTP ${res.status}`);
      }

      return res.json();
    },
  },
};

// ---- Sessions ----

export const sessionApi = {
  list: () => apiFetch<{ sessions: Session[] }>("/sessions"),
  create: (title: string) =>
    apiFetch<{ session: Session }>("/sessions", {
      method: "POST",
      body: JSON.stringify({ title }),
    }),
  delete: (id: string) => apiFetch<void>(`/sessions/${id}`, { method: "DELETE" }),
  getMessages: (id: string) => apiFetch<{ messages: Message[] }>(`/sessions/${id}/messages`),
  sendMessage: (id: string, text: string, model = "") =>
    apiFetch<{ message: Message }>(`/sessions/${id}/messages`, {
      method: "POST",
      body: JSON.stringify({ text, model }),
    }),
};

// ---- SSE stream (uses fetch + ReadableStream, not EventSource, to support auth header) ----

export async function* streamSession(
  sessionId: string,
  signal?: AbortSignal,
): AsyncGenerator<SSEEvent> {
  const token = await getAccessToken();
  if (!token) throw new ApiError(401, "Not authenticated");

  const res = await fetch(`${BASE}/sessions/${sessionId}/stream`, {
    headers: {
      Authorization: `Bearer ${token}`,
      Accept: "text/event-stream",
    },
    signal,
  });

  if (!res.ok || !res.body) {
    throw new ApiError(res.status, `Stream failed: HTTP ${res.status}`);
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      buffer = lines.pop() ?? "";

      for (const line of lines) {
        if (line.startsWith("data: ")) {
          const payload = line.slice(6).trim();
          if (!payload) continue;
          try {
            const event = JSON.parse(payload) as SSEEvent;
            yield event;
            if (event.type === "final" || event.type === "error") return;
          } catch {}
        }
      }
    }
  } finally {
    reader.cancel();
  }
}
