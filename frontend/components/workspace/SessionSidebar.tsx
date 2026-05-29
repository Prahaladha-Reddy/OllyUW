"use client";

import { useState } from "react";
import { useSessions } from "@/hooks/useSessions";
import { useSessionStore } from "@/lib/store";
import { timeAgo } from "@/lib/utils";
import { Plus, Trash } from "@phosphor-icons/react";

export default function SessionSidebar() {
  const { sessions, create, remove } = useSessions();
  const { activeId, setActiveId } = useSessionStore();
  const [creating, setCreating] = useState(false);

  async function handleCreate() {
    setCreating(true);
    try {
      await create("New session");
    } finally {
      setCreating(false);
    }
  }

  return (
    <div
      style={{
        width: 220,
        flexShrink: 0,
        borderRight: "1px solid #eaeaea",
        backgroundColor: "#ffffff",
        display: "flex",
        flexDirection: "column",
        overflow: "hidden",
      }}
    >
      {/* Header */}
      <div
        style={{
          padding: "12px 14px 10px",
          borderBottom: "1px solid #eaeaea",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
        }}
      >
        <span style={{ fontSize: 11, fontWeight: 600, color: "#787774", letterSpacing: "0.06em", textTransform: "uppercase" }}>
          Sessions
        </span>
      </div>

      {/* Session list */}
      <div style={{ flex: 1, overflowY: "auto", padding: "6px 0" }}>
        {sessions.length === 0 && (
          <p style={{ fontSize: 12, color: "#ababab", padding: "12px 14px" }}>No sessions yet.</p>
        )}

        {sessions.map((session) => {
          const active = session.id === activeId;
          return (
            <div
              key={session.id}
              onClick={() => setActiveId(session.id)}
              style={{
                padding: "8px 14px",
                cursor: "pointer",
                borderLeft: `2px solid ${active ? "#111111" : "transparent"}`,
                backgroundColor: active ? "#fbfbfa" : "transparent",
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                gap: 8,
                transition: "background-color 0.1s",
              }}
              onMouseEnter={(e) => {
                if (!active) e.currentTarget.style.backgroundColor = "#fbfbfa";
              }}
              onMouseLeave={(e) => {
                if (!active) e.currentTarget.style.backgroundColor = "transparent";
              }}
            >
              <div style={{ flex: 1, minWidth: 0 }}>
                <p
                  style={{
                    fontSize: 13,
                    fontWeight: active ? 600 : 400,
                    color: "#111111",
                    overflow: "hidden",
                    whiteSpace: "nowrap",
                    textOverflow: "ellipsis",
                    marginBottom: 1,
                  }}
                >
                  {session.title}
                </p>
                <p style={{ fontSize: 11, color: "#ababab", fontFamily: '"Geist Mono", monospace' }}>
                  {timeAgo(session.created_at)}
                </p>
              </div>

              <button
                onClick={(e) => {
                  e.stopPropagation();
                  remove(session.id);
                }}
                style={{
                  background: "none",
                  border: "none",
                  cursor: "pointer",
                  color: "#cccccc",
                  display: "flex",
                  flexShrink: 0,
                  padding: 2,
                  borderRadius: 3,
                  opacity: 0,
                  transition: "opacity 0.15s",
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.opacity = "1";
                  e.currentTarget.style.color = "#9F2F2D";
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.opacity = "0";
                  e.currentTarget.style.color = "#cccccc";
                }}
                title="Delete session"
              >
                <Trash size={13} />
              </button>
            </div>
          );
        })}
      </div>

      {/* New session */}
      <div style={{ borderTop: "1px solid #eaeaea", padding: "10px 14px" }}>
        <button
          onClick={handleCreate}
          disabled={creating}
          style={{
            display: "flex",
            alignItems: "center",
            gap: 6,
            background: "none",
            border: "none",
            cursor: creating ? "not-allowed" : "pointer",
            color: creating ? "#ababab" : "#787774",
            fontSize: 13,
            padding: "4px 0",
            transition: "color 0.15s",
          }}
          onMouseEnter={(e) => { if (!creating) e.currentTarget.style.color = "#111111"; }}
          onMouseLeave={(e) => { if (!creating) e.currentTarget.style.color = "#787774"; }}
        >
          <Plus size={13} weight="bold" />
          {creating ? "Creating..." : "New session"}
        </button>
      </div>
    </div>
  );
}
