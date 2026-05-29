"use client";

import { useRef, useEffect, useState, KeyboardEvent } from "react";
import { useChat } from "@/hooks/useChat";
import { useSessionStore, useUIStore } from "@/lib/store";
import { useSessions } from "@/hooks/useSessions";
import { PaperPlaneRight, Paperclip } from "@phosphor-icons/react";
import type { Message } from "@/types";

export default function ChatPanel() {
  const { activeId } = useSessionStore();
  const { create } = useSessions();
  const { messages, streamingText, sending, send } = useChat(activeId);
  const { setUploadModalOpen } = useUIStore();

  const [input, setInput] = useState("");
  const bottomRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Scroll to bottom on new messages.
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages.length, streamingText]);

  // Auto-grow textarea.
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

    // Auto-create a session if none exists.
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

  const isEmpty = messages.length === 0 && !streamingText;

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

        {messages.map((msg) => (
          <MessageBubble key={msg.id} message={msg} />
        ))}

        {streamingText !== null && (
          <div
            style={{
              alignSelf: "flex-start",
              maxWidth: "80%",
              padding: "8px 12px",
              borderRadius: 8,
              fontSize: 14,
              lineHeight: 1.6,
              color: "#111111",
              whiteSpace: "pre-wrap",
              wordBreak: "break-word",
            }}
          >
            {streamingText}
            <span
              style={{
                display: "inline-block",
                width: 6,
                height: 14,
                backgroundColor: "#787774",
                marginLeft: 2,
                verticalAlign: "middle",
                animation: "blink 0.9s steps(1) infinite",
              }}
            />
          </div>
        )}

        <div ref={bottomRef} style={{ height: 16 }} />
      </div>

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
          onFocusCapture={(e) => { (e.currentTarget as HTMLDivElement).style.borderColor = "#111111"; }}
          onBlurCapture={(e) => { (e.currentTarget as HTMLDivElement).style.borderColor = "#eaeaea"; }}
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

      {/* Blink keyframe injected inline */}
      <style>{`
        @keyframes blink {
          0%, 100% { opacity: 1; }
          50% { opacity: 0; }
        }
      `}</style>
    </div>
  );
}

function MessageBubble({ message }: { message: Message }) {
  const isUser = message.role === "user";

  return (
    <div
      style={{
        display: "flex",
        justifyContent: isUser ? "flex-end" : "flex-start",
        marginBottom: 2,
      }}
    >
      <div
        style={{
          maxWidth: "80%",
          padding: "8px 12px",
          borderRadius: 8,
          fontSize: 14,
          lineHeight: 1.6,
          color: isUser ? "#ffffff" : "#111111",
          backgroundColor: isUser ? "#111111" : "transparent",
          whiteSpace: "pre-wrap",
          wordBreak: "break-word",
        }}
      >
        {message.content}
      </div>
    </div>
  );
}
