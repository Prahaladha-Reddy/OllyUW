"use client";

import { useEffect } from "react";

// OAuth callback page — opened as a popup by ConnectedAppsModal.
// Composio redirects here after the user approves (or cancels) the OAuth flow.
// We send a message to the opener and close immediately.
export default function ConnectionsCallbackPage() {
  useEffect(() => {
    if (window.opener) {
      window.opener.postMessage({ type: "composio_callback", status: "success" }, "*");
      window.close();
    }
  }, []);

  return (
    <div
      style={{
        minHeight: "100dvh",
        backgroundColor: "#fbfbfa",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        gap: 16,
        fontFamily: '"Geist", "Helvetica Neue", system-ui, sans-serif',
      }}
    >
      <div
        style={{
          width: 40,
          height: 40,
          borderRadius: "50%",
          backgroundColor: "#111111",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
        }}
      >
        <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
          <path
            d="M3.5 9.5L7 13L14.5 5"
            stroke="white"
            strokeWidth="1.8"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
      </div>
      <p style={{ fontSize: 14, color: "#111111", fontWeight: 500 }}>Connected</p>
      <p style={{ fontSize: 12, color: "#787774" }}>Closing this window…</p>
    </div>
  );
}
