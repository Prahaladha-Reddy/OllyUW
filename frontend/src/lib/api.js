const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";

async function getAccessToken(session) {
  const token = session?.access_token;
  if (!token) {
    throw new Error("You need to sign in first.");
  }
  return token;
}

async function apiRequest(session, path, options = {}) {
  const token = await getAccessToken(session);
  const headers = new Headers(options.headers);
  headers.set("Authorization", `Bearer ${token}`);

  if (options.body && !(options.body instanceof FormData) && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers,
  });

  if (response.status === 204) {
    return null;
  }

  const contentType = response.headers.get("content-type") || "";
  const payload = contentType.includes("application/json") ? await response.json() : await response.text();

  if (!response.ok) {
    const detail = typeof payload === "object" ? payload.detail || payload.message : payload;
    throw new Error(detail || "Something went wrong. Try again.");
  }

  return payload;
}

export function listProjects(session) {
  return apiRequest(session, "/projects");
}

export function getComputer(session) {
  return apiRequest(session, '/computer')
}

export function listComputerFiles(session) {
  return apiRequest(session, '/computer/files')
}

export function listComputerConnections(session) {
  return apiRequest(session, '/computer/connections')
}

export function listVaultItems(session) {
  return apiRequest(session, '/computer/vault/items')
}

export function createComputerFolder(session, body) {
  return apiRequest(session, '/computer/folders', {
    method: 'POST',
    body: JSON.stringify(body),
  })
}

export function uploadComputerFiles(session, { files, relativePaths = [], parentFolderId = null }) {
  const formData = new FormData()
  files.forEach((file) => formData.append('files', file))
  relativePaths.forEach((path) => formData.append('relative_paths', path))
  if (parentFolderId) {
    formData.append('parent_folder_id', parentFolderId)
  }

  return apiRequest(session, '/computer/files', {
    method: 'POST',
    body: formData,
  })
}

export function createProject(session, body) {
  return apiRequest(session, "/projects", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export function getProject(session, projectId) {
  return apiRequest(session, `/projects/${projectId}`);
}

export function deleteProject(session, projectId) {
  return apiRequest(session, `/projects/${projectId}`, {
    method: "DELETE",
  });
}

export function uploadProjectFiles(session, projectId, files) {
  const formData = new FormData();
  files.forEach((file) => formData.append("files", file));

  return apiRequest(session, `/projects/${projectId}/files`, {
    method: "POST",
    body: formData,
  });
}

export function deleteProjectFile(session, projectId, fileId) {
  return apiRequest(session, `/projects/${projectId}/files/${fileId}`, {
    method: "DELETE",
  });
}

export function createConversation(session, projectId, body) {
  return apiRequest(session, `/projects/${projectId}/conversations`, {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export function getConversation(session, projectId, conversationId) {
  return apiRequest(session, `/projects/${projectId}/conversations/${conversationId}`);
}

export function deleteConversation(session, projectId, conversationId) {
  return apiRequest(session, `/projects/${projectId}/conversations/${conversationId}`, {
    method: "DELETE",
  });
}

export function sendConversationMessage(session, projectId, conversationId, { text, model }) {
  return apiRequest(session, `/projects/${projectId}/conversations/${conversationId}/messages`, {
    method: "POST",
    body: JSON.stringify({ text, model }),
  });
}

export function listMessages(session, projectId, conversationId) {
  return apiRequest(session, `/projects/${projectId}/conversations/${conversationId}/messages`);
}

export function uploadConversationFiles(session, projectId, conversationId, files) {
  const formData = new FormData();
  files.forEach((file) => formData.append("files", file));
  return apiRequest(session, `/projects/${projectId}/conversations/${conversationId}/files`, {
    method: "POST",
    body: formData,
  });
}

export function listWorkspaceFiles(session, projectId, conversationId) {
  return apiRequest(session, `/projects/${projectId}/conversations/${conversationId}/workspace`);
}

export async function downloadWorkspaceFile(session, projectId, conversationId, filePath) {
  const token = await getAccessToken(session);
  const url = `${API_BASE_URL}/projects/${projectId}/conversations/${conversationId}/workspace/${filePath}`;
  const response = await fetch(url, { headers: { Authorization: `Bearer ${token}` } });
  if (!response.ok) throw new Error("Download failed");
  return response.blob();
}

// SSE stream using fetch (EventSource can't set Authorization header).
// Pass an AbortSignal so the caller can close the connection on `final` —
// otherwise the backend keeps the Redis subscription open and any later
// `final` event published on that session will be persisted twice.
export async function* streamConversation(session, projectId, conversationId, signal) {
  const token = await getAccessToken(session);
  const url = `${API_BASE_URL}/projects/${projectId}/conversations/${conversationId}/stream`;

  const response = await fetch(url, {
    headers: { Authorization: `Bearer ${token}` },
    signal,
  });

  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    throw new Error(payload.detail || "Stream failed");
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      buffer = lines.pop(); // keep incomplete trailing line

      for (const line of lines) {
        if (line.startsWith("data: ")) {
          const raw = line.slice(6).trim();
          if (!raw) continue;
          try {
            yield JSON.parse(raw);
          } catch {
            // skip malformed SSE lines
          }
        }
      }
    }
  } finally {
    // Ensure the underlying connection is closed even when the consumer
    // breaks out of the loop early (e.g. on `final`).
    try { await reader.cancel(); } catch {}
  }
}
