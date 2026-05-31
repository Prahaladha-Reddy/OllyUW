"use client";

import { useRef, useEffect, useState, KeyboardEvent } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { useChat } from "@/hooks/useChat";
import { useSessionStore, useUIStore } from "@/lib/store";
import { useSessions } from "@/hooks/useSessions";
import {
  PaperPlaneRight,
  Paperclip,
  CaretDown,
  CaretRight,
  CheckCircle,
  XCircle,
  Wrench,
} from "@phosphor-icons/react";
import type { Message, MessagePart, LiveItem } from "@/types";
import type { SubagentLiveItem, SubagentToolCall } from "@/lib/store";

export default function ChatPanel() {
  const { activeId } = useSessionStore();
  const { create } = useSessions();
  const { messages, liveItems, subagents, sending, send } = useChat(activeId);
  const { setUploadModalOpen } = useUIStore();

  const [input, setInput] = useState("");
  const bottomRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages.length, liveItems.length, liveItems]);

  useEffect(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 160)}px`;
  }, [input]);

  async function handleSend() {
    const text = input.trim();
    if (!text || sending) return;
    setInput("");
    if (!activeId) {
      await create("New session");
    }
    await send(text);
  }

  function handleKeyDown(e: KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  }

  const isEmpty = messages.length === 0 && liveItems.length === 0;

  // Is the last liveItem a text item still growing?
  const lastLiveIsText =
    sending && liveItems.length > 0 && liveItems[liveItems.length - 1].kind === "text";

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
          paddingLeft: 12,
          paddingRight: 12,
          flexShrink: 0,
        }}
      >
        <span style={{ fontSize: 12, color: "#787774" }}>
          {activeId ? "Chat" : "Chat - no session"}
        </span>
      </div>

      {/* Messages */}
      <div
        style={{
          flex: 1,
          overflowY: "auto",
          padding: "16px 16px 0",
          display: "flex",
          flexDirection: "column",
          gap: 4,
        }}
      >
        {isEmpty && (
          <div
            style={{
              flex: 1,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              color: "#ababab",
              fontSize: 13,
            }}
          >
            Send a message to start
          </div>
        )}

        {/* Persisted messages — tool calls render inside MessageBubble */}
        {messages.map((msg) => (
          <MessageBubble key={msg.id} message={msg} />
        ))}

        {/* Live items — text and tool calls interleaved in arrival order */}
        {liveItems.map((item, i) => {
          if (item.kind === "text") {
            const isLast = i === liveItems.length - 1;
            const showCursor = isLast && lastLiveIsText;
            return (
              <div key={item.id} className="md-bubble" style={{ alignSelf: "flex-start", maxWidth: "85%" }}>
                <Markdown text={item.text} />
                {showCursor && (
                  <span style={{
                    display: "inline-block", width: 6, height: 14,
                    backgroundColor: "#787774", marginLeft: 2,
                    verticalAlign: "middle", animation: "blink 0.9s steps(1) infinite",
                  }} />
                )}
              </div>
            );
          }
          return <ToolCallBlock key={item.id} item={item} />;
        })}

        {/* Spinner when agent is working but no text yet */}
        {sending && liveItems.length === 0 && (
          <div style={{ display: "flex", alignItems: "center", gap: 6, padding: "8px 4px" }}>
            <span
              style={{
                display: "inline-block",
                width: 12,
                height: 12,
                border: "2px solid #e0e0e0",
                borderTopColor: "#787774",
                borderRadius: "50%",
                animation: "spin 0.7s linear infinite",
              }}
            />
            <span style={{ fontSize: 12, color: "#ababab" }}>Thinking...</span>
          </div>
        )}

        <div ref={bottomRef} style={{ height: 16 }} />
      </div>

      {/* Subagent panel — slides in above input when agents are running */}
      {subagents.length > 0 && (
        <SubagentPanel subagents={subagents} />
      )}

      {/* Input bar */}
      <div
        style={{
          borderTop: "1px solid #eaeaea",
          backgroundColor: "#ffffff",
          padding: 12,
        }}
      >
        <div
          style={{
            display: "flex",
            alignItems: "flex-end",
            gap: 8,
            border: "1px solid #eaeaea",
            borderRadius: 8,
            padding: "8px 10px",
            backgroundColor: "#fbfbfa",
            transition: "border-color 0.15s",
          }}
          onFocusCapture={(e) => {
            (e.currentTarget as HTMLDivElement).style.borderColor = "#111111";
          }}
          onBlurCapture={(e) => {
            (e.currentTarget as HTMLDivElement).style.borderColor = "#eaeaea";
          }}
        >
          <button
            onClick={() => setUploadModalOpen(true)}
            title="Upload file to workspace"
            style={{
              background: "none",
              border: "none",
              cursor: "pointer",
              color: "#ababab",
              display: "flex",
              flexShrink: 0,
              padding: "2px 0",
              transition: "color 0.15s",
            }}
            onMouseEnter={(e) => (e.currentTarget.style.color = "#111111")}
            onMouseLeave={(e) => (e.currentTarget.style.color = "#ababab")}
          >
            <Paperclip size={16} weight="regular" />
          </button>

          <textarea
            ref={textareaRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Message..."
            disabled={sending}
            rows={1}
            style={{
              flex: 1,
              background: "none",
              border: "none",
              outline: "none",
              resize: "none",
              fontSize: 14,
              lineHeight: 1.5,
              color: "#111111",
              fontFamily: "inherit",
              padding: 0,
              overflowY: "hidden",
              opacity: sending ? 0.5 : 1,
            }}
          />

          <button
            onClick={handleSend}
            disabled={!input.trim() || sending}
            title="Send (Enter)"
            style={{
              background: "none",
              border: "none",
              cursor: !input.trim() || sending ? "not-allowed" : "pointer",
              color: !input.trim() || sending ? "#cccccc" : "#111111",
              display: "flex",
              flexShrink: 0,
              padding: "2px 0",
              transition: "color 0.15s",
            }}
          >
            <PaperPlaneRight size={16} weight="fill" />
          </button>
        </div>
        <p style={{ fontSize: 11, color: "#cccccc", marginTop: 6, textAlign: "right" }}>
          Enter to send, Shift+Enter for newline
        </p>
      </div>

      <style>{`
        @keyframes blink { 0%,100%{opacity:1} 50%{opacity:0} }
        @keyframes spin  { to{transform:rotate(360deg)} }
        .md-bubble {
          padding: 8px 12px;
          border-radius: 8px;
          font-size: 14px;
          color: #111111;
          word-break: break-word;
        }
        .md-bubble > *:first-child { margin-top: 0 !important; }
        .md-bubble > *:last-child  { margin-bottom: 0 !important; }
      `}</style>
    </div>
  );
}

// ── Markdown renderer ───────────────────────────────────────────────────────

function Markdown({ text }: { text: string }) {
  return (
    <ReactMarkdown
      remarkPlugins={[remarkGfm]}
      components={{
        // Paragraphs — no extra margin on first/last
        p: ({ children }) => (
          <p style={{ margin: "0 0 8px", lineHeight: 1.65 }}>{children}</p>
        ),
        // Headings
        h1: ({ children }) => (
          <h1 style={{ fontSize: 18, fontWeight: 700, margin: "12px 0 6px", lineHeight: 1.3 }}>{children}</h1>
        ),
        h2: ({ children }) => (
          <h2 style={{ fontSize: 16, fontWeight: 700, margin: "10px 0 5px", lineHeight: 1.3 }}>{children}</h2>
        ),
        h3: ({ children }) => (
          <h3 style={{ fontSize: 14, fontWeight: 700, margin: "8px 0 4px", lineHeight: 1.3 }}>{children}</h3>
        ),
        // Inline code
        code: ({ children, className }) => {
          const isBlock = className?.startsWith("language-");
          if (isBlock) {
            return (
              <code style={{
                display: "block", overflowX: "auto",
                fontFamily: "monospace", fontSize: 12.5, lineHeight: 1.6,
                color: "#111", background: "#f4f4f2", borderRadius: 6,
                padding: "10px 12px", margin: "4px 0",
              }}>
                {children}
              </code>
            );
          }
          return (
            <code style={{
              fontFamily: "monospace", fontSize: 12.5,
              background: "#f0f0ee", borderRadius: 3,
              padding: "1px 5px", color: "#c7254e",
            }}>
              {children}
            </code>
          );
        },
        // Code blocks
        pre: ({ children }) => (
          <pre style={{ margin: "6px 0", background: "none", padding: 0 }}>{children}</pre>
        ),
        // Tables (GFM)
        table: ({ children }) => (
          <div style={{ overflowX: "auto", margin: "8px 0" }}>
            <table style={{
              borderCollapse: "collapse", fontSize: 13,
              width: "100%", lineHeight: 1.5,
            }}>
              {children}
            </table>
          </div>
        ),
        th: ({ children }) => (
          <th style={{
            border: "1px solid #ddd", padding: "6px 10px",
            textAlign: "left", backgroundColor: "#f7f7f5",
            fontWeight: 600, fontSize: 12.5,
          }}>
            {children}
          </th>
        ),
        td: ({ children }) => (
          <td style={{
            border: "1px solid #eee", padding: "5px 10px",
            fontSize: 13, verticalAlign: "top",
          }}>
            {children}
          </td>
        ),
        // Lists
        ul: ({ children }) => (
          <ul style={{ margin: "4px 0 8px", paddingLeft: 20, lineHeight: 1.7 }}>{children}</ul>
        ),
        ol: ({ children }) => (
          <ol style={{ margin: "4px 0 8px", paddingLeft: 20, lineHeight: 1.7 }}>{children}</ol>
        ),
        li: ({ children }) => (
          <li style={{ marginBottom: 2 }}>{children}</li>
        ),
        // Blockquote
        blockquote: ({ children }) => (
          <blockquote style={{
            borderLeft: "3px solid #ddd", margin: "6px 0",
            paddingLeft: 12, color: "#666", fontStyle: "italic",
          }}>
            {children}
          </blockquote>
        ),
        // Horizontal rule
        hr: () => <hr style={{ border: "none", borderTop: "1px solid #eee", margin: "10px 0" }} />,
        // Links
        a: ({ href, children }) => (
          <a href={href} target="_blank" rel="noopener noreferrer"
            style={{ color: "#0066cc", textDecoration: "underline" }}>
            {children}
          </a>
        ),
        // Strong / em
        strong: ({ children }) => <strong style={{ fontWeight: 700 }}>{children}</strong>,
        em: ({ children }) => <em style={{ fontStyle: "italic" }}>{children}</em>,
      }}
    >
      {text}
    </ReactMarkdown>
  );
}

// ── Persisted message bubble ────────────────────────────────────────────────

function MessageBubble({ message }: { message: Message }) {
  const isUser = message.role === "user";

  if (isUser) {
    return (
      <div style={{ display: "flex", justifyContent: "flex-end", marginBottom: 2 }}>
        <div
          style={{
            maxWidth: "85%",
            padding: "8px 12px",
            borderRadius: 8,
            fontSize: 14,
            lineHeight: 1.6,
            color: "#ffffff",
            backgroundColor: "#111111",
            whiteSpace: "pre-wrap",
            wordBreak: "break-word",
          }}
        >
          {message.content}
        </div>
      </div>
    );
  }

  // Assistant with parts — render text and tool calls interleaved in order.
  if (message.parts && message.parts.length > 0) {
    // Build a result map so each tool_call part can look up its tool_result.
    const resultMap = new Map<string, Extract<MessagePart, { type: "tool_result" }>>();
    for (const p of message.parts) {
      if (p.type === "tool_result") resultMap.set(p.id, p);
    }

    return (
      <div
        style={{
          display: "flex",
          flexDirection: "column",
          alignItems: "flex-start",
          marginBottom: 2,
          gap: 3,
        }}
      >
        {message.parts.map((part, i) => {
          if (part.type === "text") {
            return (
              <div key={i} className="md-bubble" style={{ maxWidth: "85%" }}>
                <Markdown text={part.text} />
              </div>
            );
          }
          if (part.type === "tool_call") {
            return (
              <PersistedToolCallChip
                key={part.id}
                call={part}
                result={resultMap.get(part.id)}
              />
            );
          }
          // tool_result parts are rendered inside their matching tool_call chip
          return null;
        })}
      </div>
    );
  }

  // Old message without parts — render with markdown.
  return (
    <div style={{ display: "flex", flexDirection: "column", alignItems: "flex-start", marginBottom: 2 }}>
      <div className="md-bubble" style={{ maxWidth: "85%" }}>
        <Markdown text={message.content} />
      </div>
    </div>
  );
}

// Persisted tool call chip — now includes output from the tool_result part.
function PersistedToolCallChip({
  call,
  result,
}: {
  call: Extract<MessagePart, { type: "tool_call" }>;
  result?: Extract<MessagePart, { type: "tool_result" }>;
}) {
  const [open, setOpen] = useState(false);
  const primaryArg = getPrimaryArg(call.tool, call.args);
  const canExpand = true;
  const isError = result?.ok === false;
  const statusColor = isError ? "#ef4444" : "#22c55e";

  return (
    <div
      style={{
        alignSelf: "flex-start",
        maxWidth: "90%",
        border: "1px solid #eaeaea",
        borderRadius: 6,
        overflow: "hidden",
        backgroundColor: "#ffffff",
        fontSize: 13,
      }}
    >
      <button
        onClick={() => setOpen((v) => !v)}
        style={{
          display: "flex",
          alignItems: "center",
          gap: 7,
          padding: "6px 10px",
          background: "none",
          border: "none",
          cursor: "pointer",
          width: "100%",
          textAlign: "left",
        }}
      >
        {isError ? (
          <XCircle size={13} weight="fill" color={statusColor} style={{ flexShrink: 0 }} />
        ) : (
          <CheckCircle size={13} weight="fill" color={statusColor} style={{ flexShrink: 0 }} />
        )}
        <Wrench size={12} color="#ababab" style={{ flexShrink: 0 }} />
        <span style={{ fontFamily: "monospace", color: "#111", fontWeight: 500 }}>
          {call.tool}
        </span>
        {primaryArg && (
          <span
            style={{
              color: "#787774",
              fontFamily: "monospace",
              fontSize: 12,
              overflow: "hidden",
              textOverflow: "ellipsis",
              whiteSpace: "nowrap",
              maxWidth: 260,
            }}
          >
            {primaryArg}
          </span>
        )}
        {canExpand && (
          <span style={{ marginLeft: "auto", color: "#ababab", flexShrink: 0 }}>
            {open ? <CaretDown size={11} /> : <CaretRight size={11} />}
          </span>
        )}
      </button>
      {open && (
        <div style={{ borderTop: "1px solid #eaeaea" }}>
          <div style={{ padding: "8px 10px", borderBottom: "1px solid #f0f0f0" }}>
            <div style={{ fontSize: 10, fontWeight: 600, letterSpacing: "0.08em", color: "#ababab", textTransform: "uppercase", marginBottom: 5 }}>
              Input
            </div>
            <pre style={{ margin: 0, fontFamily: "monospace", fontSize: 11, color: "#333", whiteSpace: "pre-wrap", wordBreak: "break-all", maxHeight: 200, overflowY: "auto", backgroundColor: "#f9f9f8", borderRadius: 4, padding: "6px 8px" }}>
              {formatInput(call.tool, call.args)}
            </pre>
          </div>
          <div style={{ padding: "8px 10px" }}>
            <div style={{ fontSize: 10, fontWeight: 600, letterSpacing: "0.08em", color: "#ababab", textTransform: "uppercase", marginBottom: 5 }}>
              {isError ? "Error" : "Result"}
            </div>
            <pre style={{ margin: 0, fontFamily: "monospace", fontSize: 11, color: isError ? "#ef4444" : "#333", whiteSpace: "pre-wrap", wordBreak: "break-all", backgroundColor: isError ? "#fff5f5" : "#f9f9f8", borderRadius: 4, padding: "6px 8px", maxHeight: 300, overflowY: "auto" }}>
              {result?.output ?? "(no output)"}
            </pre>
          </div>
        </div>
      )}
    </div>
  );
}

// ── Live tool call block ────────────────────────────────────────────────────

function ToolCallBlock({ item }: { item: Extract<LiveItem, { kind: "tool" }> }) {
  const [open, setOpen] = useState(false);

  const isDone = item.status === "done";
  const isError = item.status === "error";
  const isRunning = item.status === "running";
  const hasResult = item.output !== undefined;

  const statusColor = isDone ? "#22c55e" : isError ? "#ef4444" : "#f59e0b";
  const primaryArg = getPrimaryArg(item.tool, item.args);

  return (
    <div
      style={{
        alignSelf: "flex-start",
        maxWidth: "90%",
        border: "1px solid #eaeaea",
        borderRadius: 6,
        overflow: "hidden",
        backgroundColor: "#ffffff",
        fontSize: 13,
        marginTop: 2,
        marginBottom: 2,
      }}
    >
      {/* Header row */}
      <button
        onClick={() => hasResult && setOpen((v) => !v)}
        style={{
          display: "flex",
          alignItems: "center",
          gap: 7,
          padding: "6px 10px",
          background: "none",
          border: "none",
          cursor: hasResult ? "pointer" : "default",
          width: "100%",
          textAlign: "left",
        }}
      >
        {/* Status icon / spinner */}
        {isRunning ? (
          <span
            style={{
              display: "inline-block",
              width: 12,
              height: 12,
              border: "2px solid #f59e0b",
              borderTopColor: "transparent",
              borderRadius: "50%",
              animation: "spin 0.7s linear infinite",
              flexShrink: 0,
            }}
          />
        ) : isDone ? (
          <CheckCircle size={13} weight="fill" color={statusColor} style={{ flexShrink: 0 }} />
        ) : (
          <XCircle size={13} weight="fill" color={statusColor} style={{ flexShrink: 0 }} />
        )}

        {/* Wrench icon */}
        <Wrench size={12} color="#ababab" style={{ flexShrink: 0 }} />

        {/* Tool name */}
        <span style={{ fontFamily: "monospace", color: "#111", fontWeight: 500 }}>
          {item.tool}
        </span>

        {/* Primary arg preview */}
        {primaryArg && (
          <span
            style={{
              color: "#787774",
              fontFamily: "monospace",
              fontSize: 12,
              overflow: "hidden",
              textOverflow: "ellipsis",
              whiteSpace: "nowrap",
              maxWidth: 260,
            }}
          >
            {primaryArg}
          </span>
        )}

        {/* Expand chevron */}
        {hasResult && (
          <span style={{ marginLeft: "auto", color: "#ababab", flexShrink: 0 }}>
            {open ? <CaretDown size={11} /> : <CaretRight size={11} />}
          </span>
        )}
      </button>

      {/* Expanded body */}
      {open && (
        <div style={{ borderTop: "1px solid #eaeaea" }}>
          {/* Input section */}
          <div style={{ padding: "8px 10px", borderBottom: "1px solid #f0f0f0" }}>
            <div
              style={{
                fontSize: 10,
                fontWeight: 600,
                letterSpacing: "0.08em",
                color: "#ababab",
                textTransform: "uppercase",
                marginBottom: 5,
              }}
            >
              Input
            </div>
            <pre
              style={{
                margin: 0,
                fontFamily: "monospace",
                fontSize: 11,
                color: "#333",
                whiteSpace: "pre-wrap",
                wordBreak: "break-all",
                backgroundColor: "#f9f9f8",
                borderRadius: 4,
                padding: "6px 8px",
                maxHeight: 200,
                overflowY: "auto",
              }}
            >
              {formatInput(item.tool, item.args)}
            </pre>
          </div>

          {/* Output section */}
          <div style={{ padding: "8px 10px" }}>
            <div
              style={{
                fontSize: 10,
                fontWeight: 600,
                letterSpacing: "0.08em",
                color: "#ababab",
                textTransform: "uppercase",
                marginBottom: 5,
              }}
            >
              {isError ? "Error" : "Result"}
            </div>
            <pre
              style={{
                margin: 0,
                fontFamily: "monospace",
                fontSize: 11,
                color: isError ? "#ef4444" : "#333",
                whiteSpace: "pre-wrap",
                wordBreak: "break-all",
                backgroundColor: isError ? "#fff5f5" : "#f9f9f8",
                borderRadius: 4,
                padding: "6px 8px",
                maxHeight: 300,
                overflowY: "auto",
              }}
            >
              {item.output ?? "(no output)"}
            </pre>
          </div>
        </div>
      )}
    </div>
  );
}

// ── Helpers ─────────────────────────────────────────────────────────────────

function getPrimaryArg(tool: string, args: Record<string, unknown>): string {
  const s = (v: unknown) => (typeof v === "string" ? v : JSON.stringify(v));
  switch (tool) {
    case "write_file":
    case "read_file":
    case "edit_file":
      return s(args.path);
    case "run_shell":
      return s(args.command);
    case "list_files":
      return s(args.path ?? ".");
    case "glob_files":
    case "grep_files":
      return s(args.pattern);
    case "todo":
      return [args.action, args.text].filter(Boolean).map(s).join(" ");
    case "skill":
      return s(args.name);
    case "memory_search":
      return s(args.query);
    case "web_search":
      return s(args.query);
    case "web_research":
      return s(args.question);
    default:
      // Fall back to first arg value
      const first = Object.values(args)[0];
      return first !== undefined ? s(first) : "";
  }
}

// ── Subagent Panel ──────────────────────────────────────────────────────────

function SubagentPanel({ subagents }: { subagents: SubagentLiveItem[] }) {
  const [collapsed, setCollapsed] = useState(false);
  const running = subagents.filter((s) => s.status === "running").length;
  const done    = subagents.filter((s) => s.status === "done").length;
  const errored = subagents.filter((s) => s.status === "error").length;

  const headerLabel = running > 0
    ? `${running} running${done ? `, ${done} done` : ""}${errored ? `, ${errored} failed` : ""}`
    : errored > 0
    ? `${done} done · ${errored} failed`
    : `${done} done`;

  return (
    <div style={{
      borderTop: "1px solid #eaeaea",
      backgroundColor: "#fafaf9",
      flexShrink: 0,
      maxHeight: collapsed ? 36 : 280,
      transition: "max-height 0.2s ease",
      overflow: "hidden",
      display: "flex",
      flexDirection: "column",
    }}>
      {/* Header bar */}
      <button
        onClick={() => setCollapsed((v) => !v)}
        style={{
          height: 36,
          display: "flex",
          alignItems: "center",
          gap: 8,
          padding: "0 12px",
          background: "none",
          border: "none",
          borderBottom: collapsed ? "none" : "1px solid #eaeaea",
          cursor: "pointer",
          width: "100%",
          textAlign: "left",
          flexShrink: 0,
        }}
      >
        {running > 0 && (
          <span style={{
            display: "inline-block",
            width: 8, height: 8,
            border: "2px solid #f59e0b",
            borderTopColor: "transparent",
            borderRadius: "50%",
            animation: "spin 0.7s linear infinite",
            flexShrink: 0,
          }} />
        )}
        <span style={{ fontSize: 11, fontWeight: 600, color: "#555", letterSpacing: "0.04em", textTransform: "uppercase" }}>
          Subagents
        </span>
        <span style={{ fontSize: 11, color: "#999" }}>{headerLabel}</span>
        <span style={{ marginLeft: "auto", fontSize: 11, color: "#bbb" }}>
          {collapsed ? "▸" : "▾"}
        </span>
      </button>

      {/* Cards row */}
      {!collapsed && (
        <div style={{
          display: "flex",
          gap: 8,
          padding: "8px 10px",
          overflowX: "auto",
          overflowY: "hidden",
          flex: 1,
          alignItems: "flex-start",
        }}>
          {subagents.map((sa) => (
            <SubagentCard key={sa.id} agent={sa} />
          ))}
        </div>
      )}
    </div>
  );
}

function SubagentCard({ agent }: { agent: SubagentLiveItem }) {
  const [expanded, setExpanded] = useState(true);
  const isRunning = agent.status === "running";
  const isError   = agent.status === "error";
  const isDone    = agent.status === "done";

  const borderColor = isRunning ? "#f59e0b" : isDone ? "#22c55e" : "#ef4444";
  const dotColor    = borderColor;

  return (
    <div style={{
      minWidth: 200,
      maxWidth: 260,
      flexShrink: 0,
      border: `1px solid ${borderColor}33`,
      borderLeft: `3px solid ${borderColor}`,
      borderRadius: 6,
      backgroundColor: "#fff",
      fontSize: 12,
      overflow: "hidden",
    }}>
      {/* Card header */}
      <button
        onClick={() => setExpanded((v) => !v)}
        style={{
          width: "100%",
          display: "flex",
          alignItems: "center",
          gap: 6,
          padding: "6px 8px",
          background: "none",
          border: "none",
          cursor: "pointer",
          textAlign: "left",
        }}
      >
        {/* Status dot / spinner */}
        {isRunning ? (
          <span style={{
            display: "inline-block",
            width: 8, height: 8,
            border: `2px solid ${dotColor}`,
            borderTopColor: "transparent",
            borderRadius: "50%",
            animation: "spin 0.7s linear infinite",
            flexShrink: 0,
          }} />
        ) : (
          <span style={{
            display: "inline-block",
            width: 8, height: 8,
            borderRadius: "50%",
            backgroundColor: dotColor,
            flexShrink: 0,
          }} />
        )}

        <span style={{ fontFamily: "monospace", fontWeight: 600, color: "#222", fontSize: 11, flexShrink: 0 }}>
          {agent.label}
        </span>
        <span style={{ marginLeft: "auto", color: "#bbb", fontSize: 10, flexShrink: 0 }}>
          {expanded ? "▾" : "▸"}
        </span>
      </button>

      {/* Goal */}
      <div style={{ padding: "0 8px 4px", fontSize: 11, color: "#555", lineHeight: 1.4,
                    overflow: "hidden", textOverflow: "ellipsis", display: "-webkit-box",
                    WebkitLineClamp: 2, WebkitBoxOrient: "vertical" }}>
        {agent.goal}
      </div>

      {/* Tool calls */}
      {expanded && (
        <div style={{
          borderTop: "1px solid #f0f0f0",
          maxHeight: 160,
          overflowY: "auto",
        }}>
          {agent.calls.length === 0 && isRunning && (
            <div style={{ padding: "6px 8px", color: "#aaa", fontSize: 11 }}>initialising...</div>
          )}
          {agent.calls.map((call) => (
            <SubagentCallRow key={call.id} call={call} />
          ))}
          {(isDone || isError) && agent.summary && (
            <div style={{
              padding: "5px 8px",
              fontSize: 11,
              color: isDone ? "#166534" : "#991b1b",
              backgroundColor: isDone ? "#f0fdf4" : "#fff5f5",
              borderTop: "1px solid #f0f0f0",
              lineHeight: 1.4,
            }}>
              {agent.summary.slice(0, 200)}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function SubagentCallRow({ call }: { call: SubagentToolCall }) {
  const [open, setOpen] = useState(false);
  const isRunning = call.status === "running";
  const isError   = call.status === "error";

  return (
    <div style={{ borderBottom: "1px solid #f5f5f5" }}>
      <button
        onClick={() => call.output && setOpen((v) => !v)}
        style={{
          width: "100%",
          display: "flex",
          alignItems: "center",
          gap: 5,
          padding: "4px 8px",
          background: "none",
          border: "none",
          cursor: call.output ? "pointer" : "default",
          textAlign: "left",
        }}
      >
        {isRunning ? (
          <span style={{
            display: "inline-block",
            width: 6, height: 6,
            border: "1.5px solid #f59e0b",
            borderTopColor: "transparent",
            borderRadius: "50%",
            animation: "spin 0.7s linear infinite",
            flexShrink: 0,
          }} />
        ) : (
          <span style={{
            display: "inline-block",
            width: 6, height: 6,
            borderRadius: "50%",
            backgroundColor: isError ? "#ef4444" : "#22c55e",
            flexShrink: 0,
          }} />
        )}
        <span style={{ fontFamily: "monospace", fontSize: 10.5, color: "#333", fontWeight: 500 }}>
          {call.tool}
        </span>
        <span style={{
          fontSize: 10, color: "#888", overflow: "hidden", textOverflow: "ellipsis",
          whiteSpace: "nowrap", flex: 1,
        }}>
          {getPrimaryArg(call.tool, call.args)}
        </span>
        {call.output && (
          <span style={{ color: "#ccc", fontSize: 9, flexShrink: 0 }}>{open ? "▾" : "▸"}</span>
        )}
      </button>
      {open && call.output && (
        <pre style={{
          margin: 0, padding: "4px 8px 6px 20px",
          fontSize: 10, fontFamily: "monospace",
          color: isError ? "#dc2626" : "#444",
          backgroundColor: isError ? "#fff5f5" : "#f9f9f8",
          whiteSpace: "pre-wrap", wordBreak: "break-all",
          maxHeight: 100, overflowY: "auto",
          borderTop: "1px solid #f0f0f0",
        }}>
          {call.output.slice(0, 600)}{call.output.length > 600 ? "…" : ""}
        </pre>
      )}
    </div>
  );
}

function formatInput(tool: string, args: Record<string, unknown>): string {
  // For write_file show path + content clearly, not raw JSON
  if (tool === "write_file" && args.path && args.content) {
    return `path: ${args.path}\n\ncontent:\n${args.content}`;
  }
  if (tool === "edit_file" && args.path) {
    return `path: ${args.path}\n\nold:\n${args.old_str}\n\nnew:\n${args.new_str}`;
  }
  if (tool === "run_shell" && args.command) {
    return `$ ${args.command}`;
  }
  // Default: pretty JSON
  return JSON.stringify(args, null, 2);
}
