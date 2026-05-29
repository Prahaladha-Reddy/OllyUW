"use client";

import { useRef, useCallback, useEffect, useState } from "react";
import { useUIStore } from "@/lib/store";
import { useComputer } from "@/hooks/useComputer";
import TopBar from "./TopBar";
import SessionSidebar from "./SessionSidebar";
import DesktopPanel from "./DesktopPanel";
import ChatPanel from "./ChatPanel";
import FooterBar from "./FooterBar";
import FileUploadModal from "./FileUploadModal";

export default function WorkspaceShell() {
  const { sidebarOpen, desktopRatio, setDesktopRatio, uploadModalOpen, bumpDesktopReload } =
    useUIStore();
  const { computer, connect, keepalive } = useComputer();

  const containerRef = useRef<HTMLDivElement>(null);
  const dragging = useRef(false);
  const [isDragging, setIsDragging] = useState(false);

  // On load: if the computer has any persisted state (a live or idle-paused
  // sandbox, or a snapshot), resume it and pull a fresh desktop URL. This is
  // why a tab you left an hour ago comes back working instead of showing a
  // dead stream against a paused sandbox.
  const didConnect = useRef(false);
  useEffect(() => {
    if (didConnect.current || !computer) return;
    const resumable =
      !!computer.sandbox_id ||
      !!computer.snapshot_id ||
      computer.runtime_state === "running" ||
      computer.runtime_state === "paused";
    if (resumable) {
      didConnect.current = true;
      connect().then(() => bumpDesktopReload());
    }
  }, [computer, connect, bumpDesktopReload]);

  // While the tab is open and the sandbox is running, reset its idle timeout
  // every 60s so it never pauses mid-use. When the tab closes the pings stop
  // and the sandbox idle-pauses on its own after the timeout window.
  useEffect(() => {
    if (computer?.runtime_state !== "running") return;
    const id = setInterval(() => {
      keepalive();
    }, 60_000);
    return () => clearInterval(id);
  }, [computer?.runtime_state, keepalive]);

  const onDividerMouseDown = useCallback(() => {
    dragging.current = true;
    setIsDragging(true);
    document.body.style.cursor = "col-resize";
    document.body.style.userSelect = "none";
  }, []);

  useEffect(() => {
    const onMove = (e: MouseEvent) => {
      if (!dragging.current || !containerRef.current) return;
      const rect = containerRef.current.getBoundingClientRect();
      const raw = (e.clientX - rect.left) / rect.width;
      setDesktopRatio(Math.max(0.28, Math.min(0.78, raw)));
    };
    const onUp = () => {
      dragging.current = false;
      setIsDragging(false);
      document.body.style.cursor = "";
      document.body.style.userSelect = "";
    };
    window.addEventListener("mousemove", onMove);
    window.addEventListener("mouseup", onUp);
    return () => {
      window.removeEventListener("mousemove", onMove);
      window.removeEventListener("mouseup", onUp);
    };
  }, [setDesktopRatio]);

  return (
    <div
      style={{
        height: "100dvh",
        display: "flex",
        flexDirection: "column",
        backgroundColor: "#fbfbfa",
        overflow: "hidden",
      }}
    >
      <TopBar />

      <div ref={containerRef} style={{ flex: 1, display: "flex", overflow: "hidden" }}>
        {sidebarOpen && <SessionSidebar />}

        {/* Desktop panel */}
        <div style={{ width: `${desktopRatio * 100}%`, display: "flex", flexDirection: "column", minWidth: 280 }}>
          <DesktopPanel />
        </div>

        {/* Drag divider */}
        <div
          onMouseDown={onDividerMouseDown}
          style={{
            width: 4,
            flexShrink: 0,
            backgroundColor: isDragging ? "#aaaaaa" : "#eaeaea",
            cursor: "col-resize",
            transition: isDragging ? "none" : "background-color 0.15s",
          }}
          onMouseEnter={(e) => { if (!isDragging) e.currentTarget.style.backgroundColor = "#cccccc"; }}
          onMouseLeave={(e) => { if (!isDragging) e.currentTarget.style.backgroundColor = "#eaeaea"; }}
        />

        {/* Chat panel */}
        <div style={{ flex: 1, display: "flex", flexDirection: "column", minWidth: 300 }}>
          <ChatPanel />
        </div>
      </div>

      <FooterBar />

      {uploadModalOpen && <FileUploadModal />}
    </div>
  );
}
