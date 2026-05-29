"use client";

import { useRef, useState, useCallback, DragEvent } from "react";
import { useUIStore } from "@/lib/store";
import { useWorkspaceFolders, useUpload } from "@/hooks/useWorkspace";
import { useComputer } from "@/hooks/useComputer";
import { folderName, folderDepth } from "@/lib/utils";
import { FolderOpen, Upload, X } from "@phosphor-icons/react";

export default function FileUploadModal() {
  const { setUploadModalOpen } = useUIStore();
  const { computer } = useComputer();
  const isRunning = computer?.runtime_state === "running";

  const { folders } = useWorkspaceFolders(isRunning);
  const { upload, uploading, error } = useUpload();

  const [selectedPath, setSelectedPath] = useState("");
  const [droppedFiles, setDroppedFiles] = useState<File[]>([]);
  const [dragOver, setDragOver] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleDrop = useCallback((e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setDragOver(false);
    const files = Array.from(e.dataTransfer.files);
    if (files.length > 0) setDroppedFiles((prev) => [...prev, ...files]);
  }, []);

  const handleBrowse = useCallback(() => {
    fileInputRef.current?.click();
  }, []);

  const handleFileInput = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files ?? []);
    if (files.length > 0) setDroppedFiles((prev) => [...prev, ...files]);
    e.target.value = "";
  }, []);

  const removeFile = useCallback((index: number) => {
    setDroppedFiles((prev) => prev.filter((_, i) => i !== index));
  }, []);

  async function handleUpload() {
    if (droppedFiles.length === 0) return;
    const ok = await upload(droppedFiles, selectedPath);
    if (ok) {
      setUploadModalOpen(false);
    }
  }

  return (
    <div
      onClick={() => setUploadModalOpen(false)}
      style={{
        position: "fixed",
        inset: 0,
        backgroundColor: "rgba(0,0,0,0.25)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        zIndex: 50,
        padding: 24,
      }}
    >
      <div
        onClick={(e) => e.stopPropagation()}
        style={{
          width: "100%",
          maxWidth: 620,
          maxHeight: "80vh",
          backgroundColor: "#ffffff",
          border: "1px solid #eaeaea",
          borderRadius: 12,
          display: "flex",
          flexDirection: "column",
          overflow: "hidden",
        }}
      >
        {/* Header */}
        <div
          style={{
            padding: "16px 20px",
            borderBottom: "1px solid #eaeaea",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
          }}
        >
          <h2 style={{ fontSize: 15, fontWeight: 600, color: "#111111", letterSpacing: "-0.01em" }}>
            Upload to workspace
          </h2>
          <button
            onClick={() => setUploadModalOpen(false)}
            style={{
              background: "none",
              border: "none",
              cursor: "pointer",
              color: "#ababab",
              display: "flex",
              padding: 2,
              borderRadius: 4,
              transition: "color 0.15s",
            }}
            onMouseEnter={(e) => (e.currentTarget.style.color = "#111111")}
            onMouseLeave={(e) => (e.currentTarget.style.color = "#ababab")}
          >
            <X size={16} />
          </button>
        </div>

        <div style={{ flex: 1, display: "flex", overflow: "hidden" }}>
          {/* Folder tree */}
          <div
            style={{
              width: 200,
              borderRight: "1px solid #eaeaea",
              overflow: "auto",
              padding: "8px 0",
              flexShrink: 0,
            }}
          >
            <p
              style={{
                fontSize: 10,
                fontWeight: 600,
                color: "#ababab",
                letterSpacing: "0.07em",
                textTransform: "uppercase",
                padding: "4px 14px 8px",
              }}
            >
              Destination
            </p>

            {/* Root */}
            <FolderRow
              path=""
              label="/ (root)"
              depth={0}
              active={selectedPath === ""}
              onClick={() => setSelectedPath("")}
            />

            {/* Subdirs */}
            {folders
              .filter((f) => f !== "")
              .map((f) => (
                <FolderRow
                  key={f}
                  path={f}
                  label={folderName(f)}
                  depth={folderDepth(f)}
                  active={selectedPath === f}
                  onClick={() => setSelectedPath(f)}
                />
              ))}

            {!isRunning && (
              <p style={{ fontSize: 12, color: "#ababab", padding: "8px 14px" }}>
                Start the computer to pick folders.
              </p>
            )}
          </div>

          {/* Drop zone */}
          <div style={{ flex: 1, padding: 16, display: "flex", flexDirection: "column", gap: 12 }}>
            {/* Active path */}
            <p style={{ fontSize: 11, fontFamily: '"Geist Mono", monospace', color: "#787774" }}>
              workspace/{selectedPath ? selectedPath + "/" : ""}
            </p>

            {/* Drop target */}
            <div
              onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
              onDragLeave={() => setDragOver(false)}
              onDrop={handleDrop}
              onClick={handleBrowse}
              style={{
                flex: droppedFiles.length === 0 ? 1 : "none",
                minHeight: 100,
                border: `2px dashed ${dragOver ? "#111111" : "#eaeaea"}`,
                borderRadius: 8,
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
                justifyContent: "center",
                gap: 8,
                cursor: "pointer",
                transition: "border-color 0.15s",
                padding: 20,
              }}
              onMouseEnter={(e) => {
                if (!dragOver) (e.currentTarget as HTMLDivElement).style.borderColor = "#cccccc";
              }}
              onMouseLeave={(e) => {
                if (!dragOver) (e.currentTarget as HTMLDivElement).style.borderColor = "#eaeaea";
              }}
            >
              <Upload size={24} color="#cccccc" weight="thin" />
              <p style={{ fontSize: 13, color: "#787774", textAlign: "center" }}>
                Drop files here or{" "}
                <span style={{ color: "#111111", textDecoration: "underline" }}>browse</span>
              </p>
              <input
                ref={fileInputRef}
                type="file"
                multiple
                style={{ display: "none" }}
                onChange={handleFileInput}
              />
            </div>

            {/* File list */}
            {droppedFiles.length > 0 && (
              <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
                {droppedFiles.map((file, i) => (
                  <div
                    key={i}
                    style={{
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "space-between",
                      padding: "6px 10px",
                      backgroundColor: "#fbfbfa",
                      borderRadius: 6,
                      border: "1px solid #eaeaea",
                    }}
                  >
                    <span style={{ fontSize: 12, color: "#111111", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", flex: 1 }}>
                      {file.name}
                    </span>
                    <span style={{ fontSize: 11, fontFamily: '"Geist Mono", monospace', color: "#ababab", marginLeft: 10, flexShrink: 0 }}>
                      {(file.size / 1024).toFixed(0)}KB
                    </span>
                    <button
                      onClick={() => removeFile(i)}
                      style={{
                        background: "none",
                        border: "none",
                        cursor: "pointer",
                        color: "#cccccc",
                        marginLeft: 8,
                        display: "flex",
                        transition: "color 0.15s",
                        flexShrink: 0,
                        padding: 2,
                      }}
                      onMouseEnter={(e) => (e.currentTarget.style.color = "#9F2F2D")}
                      onMouseLeave={(e) => (e.currentTarget.style.color = "#cccccc")}
                    >
                      <X size={12} />
                    </button>
                  </div>
                ))}
              </div>
            )}

            {error && (
              <p
                style={{
                  fontSize: 12,
                  color: "#9F2F2D",
                  backgroundColor: "#FDEBEC",
                  padding: "8px 12px",
                  borderRadius: 6,
                }}
              >
                {error}
              </p>
            )}
          </div>
        </div>

        {/* Footer */}
        <div
          style={{
            padding: "12px 20px",
            borderTop: "1px solid #eaeaea",
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
          }}
        >
          <button
            onClick={() => setUploadModalOpen(false)}
            style={{
              background: "none",
              border: "none",
              cursor: "pointer",
              fontSize: 13,
              color: "#787774",
              padding: "6px 0",
              transition: "color 0.15s",
            }}
            onMouseEnter={(e) => (e.currentTarget.style.color = "#111111")}
            onMouseLeave={(e) => (e.currentTarget.style.color = "#787774")}
          >
            Cancel
          </button>

          <button
            onClick={handleUpload}
            disabled={droppedFiles.length === 0 || uploading || !isRunning}
            style={{
              backgroundColor: "#111111",
              color: "#ffffff",
              fontSize: 13,
              fontWeight: 500,
              padding: "8px 18px",
              border: "none",
              borderRadius: 6,
              cursor: droppedFiles.length === 0 || uploading || !isRunning ? "not-allowed" : "pointer",
              opacity: droppedFiles.length === 0 || uploading || !isRunning ? 0.4 : 1,
              transition: "opacity 0.15s, background-color 0.15s",
            }}
            onMouseEnter={(e) => {
              if (droppedFiles.length > 0 && !uploading && isRunning) {
                e.currentTarget.style.backgroundColor = "#333333";
              }
            }}
            onMouseLeave={(e) => (e.currentTarget.style.backgroundColor = "#111111")}
          >
            {uploading
              ? "Uploading..."
              : !isRunning
              ? "Start computer first"
              : `Upload ${droppedFiles.length > 0 ? `${droppedFiles.length} file${droppedFiles.length > 1 ? "s" : ""}` : ""}`}
          </button>
        </div>
      </div>
    </div>
  );
}

function FolderRow({
  label,
  depth,
  active,
  onClick,
}: {
  path: string;
  label: string;
  depth: number;
  active: boolean;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      style={{
        display: "flex",
        alignItems: "center",
        gap: 6,
        width: "100%",
        padding: `5px 14px 5px ${14 + depth * 14}px`,
        background: "none",
        border: "none",
        cursor: "pointer",
        textAlign: "left",
        fontSize: 12,
        color: active ? "#111111" : "#787774",
        fontWeight: active ? 600 : 400,
        backgroundColor: active ? "#fbfbfa" : "transparent",
        borderLeft: `2px solid ${active ? "#111111" : "transparent"}`,
        transition: "background-color 0.1s, color 0.1s",
      }}
      onMouseEnter={(e) => {
        if (!active) {
          e.currentTarget.style.backgroundColor = "#fbfbfa";
          e.currentTarget.style.color = "#111111";
        }
      }}
      onMouseLeave={(e) => {
        if (!active) {
          e.currentTarget.style.backgroundColor = "transparent";
          e.currentTarget.style.color = "#787774";
        }
      }}
    >
      <FolderOpen size={13} weight={active ? "fill" : "regular"} />
      {label}
    </button>
  );
}
