"use client";

import { useEffect, useRef, useCallback } from "react";
import useSWR from "swr";
import { sessionApi, streamSession } from "@/lib/api";
import { useChatStore } from "@/lib/store";
import type { Message } from "@/types";

export function useChat(sessionId: string | null) {
  const {
    messages,
    liveItems,
    subagents,
    sending,
    setMessages,
    appendMessage,
    setSending,
    pushTextChunk,
    pushToolCall,
    updateToolCall,
    clearLiveItems,
    clearForSession,
    pushSubagent,
    updateSubagent,
    pushSubagentCall,
    updateSubagentCall,
  } = useChatStore();

  const abortRef = useRef<AbortController | null>(null);

  const { mutate } = useSWR(
    sessionId ? `messages:${sessionId}` : null,
    () => sessionApi.getMessages(sessionId!),
    {
      revalidateOnFocus: false,
      onSuccess: (data) => setMessages(data.messages),
    },
  );

  useEffect(() => {
    clearForSession();
  }, [sessionId, clearForSession]);

  useEffect(() => {
    return () => {
      abortRef.current?.abort();
    };
  }, []);

  const send = useCallback(
    async (text: string, model = "") => {
      if (!sessionId || sending) return;

      setSending(true);
      clearLiveItems();

      const optimistic: Message = {
        id: `tmp-${crypto.randomUUID()}`,
        session_id: sessionId,
        user_id: "",
        role: "user",
        content: text,
        model: model || null,
        citations: null,
        parts: null,
        created_at: new Date().toISOString(),
      };
      appendMessage(optimistic);

      let finalMessage: Message | null = null;

      try {
        // POST first — see main branch comment about React Strict Mode / AbortController ordering.
        await sessionApi.sendMessage(sessionId, text, model);

        abortRef.current?.abort();
        const ctrl = new AbortController();
        abortRef.current = ctrl;

        for await (const event of streamSession(sessionId, ctrl.signal)) {
          if (event.type === "text_delta") {
            pushTextChunk(event.text ?? "");
          } else if (event.type === "subagent_start") {
            pushSubagent({
              id: event.subagent_id ?? crypto.randomUUID(),
              label: event.subagent_label ?? event.subagent_id ?? "agent",
              goal: event.goal ?? "",
              toolsets: event.toolsets ?? [],
              status: "running",
              calls: [],
            });
          } else if (event.type === "subagent_done") {
            updateSubagent(event.subagent_id ?? "", {
              status: event.success ? "done" : "error",
              summary: event.summary,
            });
          } else if (event.type === "tool_call") {
            if (event.subagent_id) {
              // Route to subagent panel
              pushSubagentCall(event.subagent_id, {
                id: event.id ?? crypto.randomUUID(),
                tool: event.tool ?? "",
                args: event.args ?? {},
                status: "running",
              });
            } else {
              pushToolCall({
                kind: "tool",
                id: event.id ?? crypto.randomUUID(),
                tool: event.tool ?? "",
                args: event.args ?? {},
                status: "running",
              });
            }
          } else if (event.type === "tool_result") {
            if (event.subagent_id) {
              updateSubagentCall(event.subagent_id, event.id ?? "", {
                status: event.ok ? "done" : "error",
                output: event.output,
              });
            } else {
              updateToolCall(event.id ?? "", {
                status: event.ok ? "done" : "error",
                output: event.output,
              });
            }
          } else if (event.type === "final") {
            finalMessage = {
              id: event.id ?? crypto.randomUUID(),
              session_id: sessionId,
              user_id: event.user_id ?? "",
              role: "assistant",
              content: event.text ?? "",
              model: event.model ?? null,
              citations: event.citations ?? null,
              parts: null, // real parts come from mutate() after DB save
              created_at: event.created_at ?? new Date().toISOString(),
            };
            break;
          } else if (event.type === "error") {
            throw new Error(event.text ?? "Stream error");
          }
        }

        // Clear live items — tool_calls are now in the DB row returned by mutate(),
        // so PersistedToolCallChip renders them permanently from messages.
        clearLiveItems();
        if (finalMessage) appendMessage(finalMessage);
        await mutate();
      } catch (err) {
        if ((err as Error).name !== "AbortError") {
          clearLiveItems();
          console.error("Chat error:", err);
        }
      } finally {
        abortRef.current?.abort();
        setSending(false);
      }
    },
    [
      sessionId,
      sending,
      mutate,
      setSending,
      clearLiveItems,
      appendMessage,
      pushTextChunk,
      pushToolCall,
      updateToolCall,
      pushSubagent,
      updateSubagent,
      pushSubagentCall,
      updateSubagentCall,
    ],
  );

  return { messages, liveItems, subagents, sending, send };
}
