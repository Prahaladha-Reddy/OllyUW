"use client";

import { useComputer } from "@/hooks/useComputer";
import { useSessions } from "@/hooks/useSessions";
import { Pause, Camera } from "@phosphor-icons/react";
import { useState } from "react";

export default function FooterBar() {
  const { computer, pause, snapshot } = useComputer();
  const { create } = useSessions();
  const [pausing, setPausing] = useState(false);

  async function handlePause() {
    setPausing(true);
    try {
      await pause();
    } finally {
      setPausing(false);
    }
  }

  return (
    <div
      style={{
        height: 40,
        borderTop: "1px solid #eaeaea",
        backgroundColor: "#ffffff",
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        paddingLeft: 16,
        paddingRight: 16,
        flexShrink: 0,
      }}
    >
      {/* Left: new session */}
      <button
        onClick={() => create()}
        style={{
          background: "none",
          border: "none",
          cursor: "pointer",
          fontSize: 12,
          color: "#787774",
          padding: 0,
          transition: "color 0.15s",
        }}
        onMouseEnter={(e) => (e.currentTarget.style.color = "#111111")}
        onMouseLeave={(e) => (e.currentTarget.style.color = "#787774")}
      >
        + New session
      </button>

      {/* Center: workspace path */}
      <span
        style={{
          fontSize: 11,
          fontFamily: '"Geist Mono", "SF Mono", monospace',
          color: "#cccccc",
        }}
      >
        {computer?.workspace_path ?? "/home/user/workspace"}
      </span>

      {/* Right: pause + snapshot */}
      <div style={{ display: "flex", gap: 12, alignItems: "center" }}>
        {computer?.runtime_state === "running" && (
          <>
            <button
              onClick={snapshot}
              title="Save snapshot"
              style={{
                background: "none",
                border: "none",
                cursor: "pointer",
                color: "#ababab",
                display: "flex",
                gap: 5,
                alignItems: "center",
                fontSize: 12,
                transition: "color 0.15s",
                padding: 0,
              }}
              onMouseEnter={(e) => (e.currentTarget.style.color = "#111111")}
              onMouseLeave={(e) => (e.currentTarget.style.color = "#ababab")}
            >
              <Camera size={13} />
              Snapshot
            </button>

            <button
              onClick={handlePause}
              disabled={pausing}
              title="Pause computer"
              style={{
                background: "none",
                border: "none",
                cursor: pausing ? "not-allowed" : "pointer",
                color: pausing ? "#cccccc" : "#787774",
                display: "flex",
                gap: 5,
                alignItems: "center",
                fontSize: 12,
                transition: "color 0.15s",
                padding: 0,
              }}
              onMouseEnter={(e) => { if (!pausing) e.currentTarget.style.color = "#111111"; }}
              onMouseLeave={(e) => { if (!pausing) e.currentTarget.style.color = "#787774"; }}
            >
              <Pause size={13} weight="fill" />
              {pausing ? "Pausing..." : "Pause"}
            </button>
          </>
        )}
      </div>
    </div>
  );
}
