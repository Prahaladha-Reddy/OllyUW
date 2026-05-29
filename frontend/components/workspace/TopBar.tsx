"use client";

import { useAuth } from "@/hooks/useAuth";
import { useComputer } from "@/hooks/useComputer";
import { useSessions } from "@/hooks/useSessions";
import { useUIStore } from "@/lib/store";
import { useSessionStore } from "@/lib/store";
import { runtimeBadge } from "@/lib/utils";
import { List, SignOut } from "@phosphor-icons/react";

export default function TopBar() {
  const { signOut } = useAuth();
  const { computer } = useComputer();
  const { sessions } = useSessions();
  const { activeId, setActiveId } = useSessionStore();
  const { sidebarOpen, setSidebarOpen } = useUIStore();

  const badge = runtimeBadge(computer?.runtime_state ?? "stopped");

  return (
    <div
      style={{
        height: 48,
        borderBottom: "1px solid #eaeaea",
        backgroundColor: "#ffffff",
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        paddingLeft: 16,
        paddingRight: 20,
        flexShrink: 0,
        gap: 12,
      }}
    >
      {/* Left: sidebar toggle + window dots + brand */}
      <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
        <button
          onClick={() => setSidebarOpen(!sidebarOpen)}
          style={{
            background: "none",
            border: "none",
            cursor: "pointer",
            color: "#787774",
            display: "flex",
            padding: 4,
            borderRadius: 4,
          }}
          title={sidebarOpen ? "Close sidebar" : "Open sidebar"}
        >
          <List size={16} weight="regular" />
        </button>

        {/* macOS-style window dots */}
        <div style={{ display: "flex", gap: 5 }}>
          <span style={{ width: 10, height: 10, borderRadius: "50%", backgroundColor: "#eaeaea", display: "block" }} />
          <span style={{ width: 10, height: 10, borderRadius: "50%", backgroundColor: "#eaeaea", display: "block" }} />
          <span style={{ width: 10, height: 10, borderRadius: "50%", backgroundColor: "#eaeaea", display: "block" }} />
        </div>

        <span
          style={{
            fontSize: 13,
            fontWeight: 600,
            color: "#111111",
            letterSpacing: "-0.01em",
          }}
        >
          Second PC
        </span>
      </div>

      {/* Center: session switcher */}
      <div style={{ flex: 1, display: "flex", justifyContent: "center" }}>
        {sessions.length > 0 && (
          <select
            value={activeId ?? ""}
            onChange={(e) => setActiveId(e.target.value || null)}
            style={{
              fontSize: 13,
              border: "1px solid #eaeaea",
              borderRadius: 6,
              padding: "4px 28px 4px 10px",
              backgroundColor: "#fbfbfa",
              color: "#111111",
              cursor: "pointer",
              appearance: "auto",
              maxWidth: 220,
            }}
          >
            <option value="" disabled>
              Select session
            </option>
            {sessions.map((s) => (
              <option key={s.id} value={s.id}>
                {s.title}
              </option>
            ))}
          </select>
        )}
      </div>

      {/* Right: status badge + sign out */}
      <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
        <span
          style={{
            fontSize: 11,
            fontWeight: 500,
            padding: "3px 8px",
            borderRadius: 9999,
            backgroundColor: badge.bg,
            color: badge.color,
            letterSpacing: "0.03em",
          }}
        >
          {badge.label}
        </span>

        <button
          onClick={signOut}
          style={{
            background: "none",
            border: "none",
            cursor: "pointer",
            color: "#787774",
            display: "flex",
            padding: 4,
            borderRadius: 4,
          }}
          title="Sign out"
        >
          <SignOut size={15} weight="regular" />
        </button>
      </div>
    </div>
  );
}
