"use client";

import { useState } from "react";
import { useAuth } from "@/hooks/useAuth";
import { useComputer } from "@/hooks/useComputer";
import { useSessions } from "@/hooks/useSessions";
import { useConnections } from "@/hooks/useConnections";
import { useUIStore, useSessionStore } from "@/lib/store";
import { runtimeBadge } from "@/lib/utils";
import { List, SignOut, PlugsConnected } from "@phosphor-icons/react";
import ConnectedAppsModal from "./ConnectedAppsModal";

export default function TopBar() {
  const { signOut } = useAuth();
  const { computer } = useComputer();
  const { sessions } = useSessions();
  const { activeId, setActiveId } = useSessionStore();
  const { sidebarOpen, setSidebarOpen } = useUIStore();
  const { connected } = useConnections();
  const [appsOpen, setAppsOpen] = useState(false);

  const badge = runtimeBadge(computer?.runtime_state ?? "stopped");

  return (
    <>
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
            style={{ background: "none", border: "none", cursor: "pointer", color: "#787774", display: "flex", padding: 4, borderRadius: 4 }}
            title={sidebarOpen ? "Close sidebar" : "Open sidebar"}
          >
            <List size={16} weight="regular" />
          </button>

          <div style={{ display: "flex", gap: 5 }}>
            <span style={{ width: 10, height: 10, borderRadius: "50%", backgroundColor: "#eaeaea", display: "block" }} />
            <span style={{ width: 10, height: 10, borderRadius: "50%", backgroundColor: "#eaeaea", display: "block" }} />
            <span style={{ width: 10, height: 10, borderRadius: "50%", backgroundColor: "#eaeaea", display: "block" }} />
          </div>

          <span style={{ fontSize: 13, fontWeight: 600, color: "#111111", letterSpacing: "-0.01em" }}>
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
              <option value="" disabled>Select session</option>
              {sessions.map((s) => (
                <option key={s.id} value={s.id}>{s.title}</option>
              ))}
            </select>
          )}
        </div>

        {/* Right: connected apps + status badge + sign out */}
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          {/* Connected Apps button */}
          <button
            onClick={() => setAppsOpen(true)}
            title="Connected Apps"
            style={{
              display: "flex",
              alignItems: "center",
              gap: 6,
              background: "none",
              border: "1px solid #eaeaea",
              cursor: "pointer",
              color: "#787774",
              borderRadius: 6,
              padding: "4px 10px",
              fontSize: 12,
              transition: "border-color 0.15s, color 0.15s",
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.borderColor = "#111111";
              e.currentTarget.style.color = "#111111";
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.borderColor = "#eaeaea";
              e.currentTarget.style.color = "#787774";
            }}
          >
            <PlugsConnected size={14} weight="regular" />
            <span>Apps</span>
            {connected.length > 0 && (
              <span
                style={{
                  backgroundColor: "#111111",
                  color: "#ffffff",
                  borderRadius: 9999,
                  fontSize: 10,
                  fontWeight: 600,
                  padding: "1px 5px",
                  lineHeight: 1.4,
                }}
              >
                {connected.length}
              </span>
            )}
          </button>

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
            style={{ background: "none", border: "none", cursor: "pointer", color: "#787774", display: "flex", padding: 4, borderRadius: 4 }}
            title="Sign out"
          >
            <SignOut size={15} weight="regular" />
          </button>
        </div>
      </div>

      {appsOpen && <ConnectedAppsModal onClose={() => setAppsOpen(false)} />}
    </>
  );
}
