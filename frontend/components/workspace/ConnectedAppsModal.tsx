"use client";

import { useState } from "react";
import { X, PlugsConnected, Plus } from "@phosphor-icons/react";
import { connectionsApi } from "@/lib/api";
import { connectApp, useConnections } from "@/hooks/useConnections";

const POPULAR_APPS: { slug: string; name: string; color: string; letter: string }[] = [
  // Google
  { slug: "gmail",        name: "Gmail",        color: "#EA4335", letter: "G" },
  { slug: "googledrive",  name: "Drive",        color: "#0F9D58", letter: "D" },
  { slug: "googlesheets", name: "Sheets",       color: "#34A853", letter: "S" },
  // Comms
  { slug: "slack",        name: "Slack",        color: "#4A154B", letter: "S" },
  { slug: "discord",      name: "Discord",      color: "#5865F2", letter: "D" },
  { slug: "telegram",     name: "Telegram",     color: "#26A5E4", letter: "T" },
  { slug: "zoom",         name: "Zoom",         color: "#2D8CFF", letter: "Z" },
  { slug: "whatsapp",     name: "WhatsApp",     color: "#25D366", letter: "W" },
  // Social
  { slug: "linkedin",     name: "LinkedIn",     color: "#0A66C2", letter: "in" },
  { slug: "instagram",    name: "Instagram",    color: "#E1306C", letter: "ig" },
  { slug: "reddit",       name: "Reddit",       color: "#FF4500", letter: "R" },
  { slug: "youtube",      name: "YouTube",      color: "#FF0000", letter: "▶" },
  // Dev & productivity
  { slug: "github",       name: "GitHub",       color: "#24292E", letter: "G" },
  { slug: "linear",       name: "Linear",       color: "#5E6AD2", letter: "L" },
  { slug: "jira",         name: "Jira",         color: "#0052CC", letter: "J" },
  { slug: "notion",       name: "Notion",       color: "#000000", letter: "N" },
  { slug: "calendly",     name: "Calendly",     color: "#006BFF", letter: "C" },
  { slug: "dropbox",      name: "Dropbox",      color: "#0061FF", letter: "D" },
];

interface Props {
  onClose: () => void;
}

export default function ConnectedAppsModal({ onClose }: Props) {
  const { connected, refresh } = useConnections();
  const [connecting, setConnecting] = useState<string | null>(null);
  const [disconnecting, setDisconnecting] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const connectedSlugs = new Set(connected.map((c) => c.slug));

  async function handleConnect(slug: string) {
    setError(null);
    setConnecting(slug);
    try {
      await connectApp(slug, () => {
        refresh();
        setConnecting(null);
      });
    } catch (e) {
      setError(e instanceof Error ? e.message : "Connection failed");
      setConnecting(null);
    }
  }

  async function handleDisconnect(slug: string) {
    setError(null);
    setDisconnecting(slug);
    try {
      await connectionsApi.disconnect(slug);
      await refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Disconnect failed");
    } finally {
      setDisconnecting(null);
    }
  }

  return (
    <div
      style={{
        position: "fixed",
        inset: 0,
        backgroundColor: "rgba(0,0,0,0.3)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        zIndex: 100,
        padding: 24,
      }}
      onClick={(e) => e.target === e.currentTarget && onClose()}
    >
      <div
        style={{
          width: "100%",
          maxWidth: 520,
          backgroundColor: "#ffffff",
          border: "1px solid #eaeaea",
          borderRadius: 12,
          boxShadow: "0 8px 32px rgba(0,0,0,0.12)",
          display: "flex",
          flexDirection: "column",
          maxHeight: "80vh",
          overflow: "hidden",
        }}
      >
        {/* Header */}
        <div
          style={{
            padding: "20px 24px 16px",
            borderBottom: "1px solid #eaeaea",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            flexShrink: 0,
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <PlugsConnected size={18} weight="duotone" color="#111111" />
            <span style={{ fontSize: 15, fontWeight: 600, color: "#111111", letterSpacing: "-0.01em" }}>
              Connected Apps
            </span>
          </div>
          <button
            onClick={onClose}
            style={{ background: "none", border: "none", cursor: "pointer", color: "#787774", display: "flex", padding: 4, borderRadius: 4 }}
          >
            <X size={16} weight="bold" />
          </button>
        </div>

        {/* Body */}
        <div style={{ padding: "16px 24px 24px", overflowY: "auto" }}>
          <p style={{ fontSize: 12, color: "#787774", marginBottom: 20, lineHeight: 1.5 }}>
            Connect apps so the agent can send emails, create issues, post messages, and more.
            Your credentials are stored securely and never shared.
          </p>

          {error && (
            <div style={{ fontSize: 12, color: "#9F2F2D", backgroundColor: "#FDEBEC", padding: "8px 12px", borderRadius: 6, marginBottom: 16 }}>
              {error}
            </div>
          )}

          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            {POPULAR_APPS.map((app) => {
              const isConnected = connectedSlugs.has(app.slug);
              const isConnecting = connecting === app.slug;
              const isDisconnecting = disconnecting === app.slug;
              const busy = isConnecting || isDisconnecting;

              return (
                <div
                  key={app.slug}
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: 12,
                    padding: "10px 14px",
                    border: `1px solid ${isConnected ? "#c8e6c9" : "#eaeaea"}`,
                    borderRadius: 8,
                    backgroundColor: isConnected ? "#f1f8f2" : "#fbfbfa",
                  }}
                >
                  {/* Icon */}
                  <div
                    style={{
                      width: 32,
                      height: 32,
                      borderRadius: 8,
                      backgroundColor: app.color,
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      flexShrink: 0,
                      color: "#ffffff",
                      fontSize: 13,
                      fontWeight: 700,
                    }}
                  >
                    {app.letter}
                  </div>

                  {/* Name + status */}
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ fontSize: 13, fontWeight: 500, color: "#111111" }}>{app.name}</div>
                    {isConnected && (
                      <div style={{ fontSize: 11, color: "#4a7c59", marginTop: 1 }}>Connected</div>
                    )}
                  </div>

                  {/* Button */}
                  {isConnected ? (
                    <button
                      onClick={() => handleDisconnect(app.slug)}
                      disabled={busy}
                      style={{
                        fontSize: 12,
                        color: busy ? "#ababab" : "#787774",
                        backgroundColor: "transparent",
                        border: "1px solid #eaeaea",
                        borderRadius: 6,
                        padding: "5px 10px",
                        cursor: busy ? "not-allowed" : "pointer",
                        flexShrink: 0,
                      }}
                    >
                      {isDisconnecting ? "Removing…" : "Disconnect"}
                    </button>
                  ) : (
                    <button
                      onClick={() => handleConnect(app.slug)}
                      disabled={busy}
                      style={{
                        fontSize: 12,
                        fontWeight: 500,
                        color: busy ? "#ababab" : "#ffffff",
                        backgroundColor: busy ? "#d4d4d4" : "#111111",
                        border: "none",
                        borderRadius: 6,
                        padding: "5px 10px",
                        cursor: busy ? "not-allowed" : "pointer",
                        display: "flex",
                        alignItems: "center",
                        gap: 4,
                        flexShrink: 0,
                      }}
                    >
                      {isConnecting ? (
                        "Connecting…"
                      ) : (
                        <>
                          <Plus size={11} weight="bold" />
                          Connect
                        </>
                      )}
                    </button>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
}
