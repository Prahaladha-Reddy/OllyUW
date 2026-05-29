"use client";

import { useComputer } from "@/hooks/useComputer";
import { useUIStore } from "@/lib/store";
import { runtimeBadge } from "@/lib/utils";
import { Monitor, ArrowsOut } from "@phosphor-icons/react";
import { useState } from "react";

export default function DesktopPanel() {
  const { computer, loading, error, start } = useComputer();
  const { desktopReloadKey, bumpDesktopReload } = useUIStore();
  const [starting, setStarting] = useState(false);
  const [fullscreen, setFullscreen] = useState(false);

  const state = computer?.runtime_state ?? "stopped";
  const badge = runtimeBadge(state);
  const isRunning = state === "running" && !!computer?.desktop_url;
  // While a start/reconnect is in flight against a running computer, show a
  // reconnecting state instead of an iframe pointed at a not-yet-live stream.
  const reconnecting = isRunning && loading;

  async function handleStart() {
    setStarting(true);
    try {
      await start();
      bumpDesktopReload();
    } finally {
      setStarting(false);
    }
  }

  if (fullscreen && isRunning) {
    return (
      <div
        style={{
          position: "fixed",
          inset: 0,
          zIndex: 100,
          backgroundColor: "#000000",
          display: "flex",
          flexDirection: "column",
        }}
      >
        <button
          onClick={() => setFullscreen(false)}
          style={{
            position: "absolute",
            top: 12,
            right: 12,
            background: "rgba(0,0,0,0.5)",
            border: "1px solid rgba(255,255,255,0.15)",
            color: "#ffffff",
            cursor: "pointer",
            borderRadius: 6,
            padding: "4px 10px",
            fontSize: 12,
            zIndex: 101,
          }}
        >
          Exit fullscreen
        </button>
        <iframe
          key={desktopReloadKey}
          src={computer!.desktop_url!}
          style={{ flex: 1, border: "none", width: "100%", height: "100%" }}
          title="Remote Desktop"
          allow="clipboard-read; clipboard-write"
        />
      </div>
    );
  }

  return (
    <div
      style={{
        flex: 1,
        display: "flex",
        flexDirection: "column",
        backgroundColor: "#fbfbfa",
        overflow: "hidden",
      }}
    >
      {/* Panel header */}
      <div
        style={{
          height: 36,
          borderBottom: "1px solid #eaeaea",
          backgroundColor: "#ffffff",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          paddingLeft: 12,
          paddingRight: 12,
          flexShrink: 0,
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <Monitor size={14} color="#787774" weight="regular" />
          <span style={{ fontSize: 12, color: "#787774" }}>Desktop</span>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <span
            style={{
              fontSize: 10,
              fontWeight: 500,
              padding: "2px 7px",
              borderRadius: 9999,
              backgroundColor: badge.bg,
              color: badge.color,
              letterSpacing: "0.03em",
            }}
          >
            {badge.label}
          </span>
          {isRunning && (
            <button
              onClick={() => setFullscreen(true)}
              title="Fullscreen"
              style={{
                background: "none",
                border: "none",
                cursor: "pointer",
                color: "#787774",
                display: "flex",
                padding: 2,
                borderRadius: 3,
              }}
            >
              <ArrowsOut size={13} />
            </button>
          )}
        </div>
      </div>

      {/* Panel body */}
      <div style={{ flex: 1, overflow: "hidden", position: "relative" }}>
        {reconnecting ? (
          <div
            style={{
              height: "100%",
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              justifyContent: "center",
              gap: 10,
            }}
          >
            <Monitor size={36} color="#cccccc" weight="thin" />
            <p style={{ fontSize: 13, color: "#787774" }}>Reconnecting to your desktop...</p>
          </div>
        ) : isRunning ? (
          <iframe
            key={desktopReloadKey}
            src={computer!.desktop_url!}
            style={{ width: "100%", height: "100%", border: "none", display: "block" }}
            title="Remote Desktop"
            allow="clipboard-read; clipboard-write"
          />
        ) : (
          <div
            style={{
              height: "100%",
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              justifyContent: "center",
              gap: 16,
            }}
          >
            <Monitor size={40} color="#cccccc" weight="thin" />

            {error && (
              <p
                style={{
                  fontSize: 12,
                  color: "#9F2F2D",
                  backgroundColor: "#FDEBEC",
                  padding: "6px 12px",
                  borderRadius: 6,
                  maxWidth: 260,
                  textAlign: "center",
                }}
              >
                {error}
              </p>
            )}

            {state === "starting" ? (
              <div style={{ textAlign: "center" }}>
                <p style={{ fontSize: 13, color: "#787774", marginBottom: 6 }}>
                  Starting desktop...
                </p>
                <p style={{ fontSize: 11, color: "#ababab" }}>This takes about 60 seconds</p>
              </div>
            ) : (
              <button
                onClick={handleStart}
                disabled={starting || loading}
                style={{
                  backgroundColor: "#111111",
                  color: "#ffffff",
                  fontSize: 13,
                  fontWeight: 500,
                  padding: "9px 20px",
                  border: "none",
                  borderRadius: 6,
                  cursor: starting || loading ? "not-allowed" : "pointer",
                  opacity: starting || loading ? 0.6 : 1,
                  transition: "opacity 0.15s, background-color 0.15s",
                }}
                onMouseEnter={(e) => {
                  if (!starting && !loading) e.currentTarget.style.backgroundColor = "#333333";
                }}
                onMouseLeave={(e) => (e.currentTarget.style.backgroundColor = "#111111")}
              >
                {starting ? "Starting..." : "Start desktop"}
              </button>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
