"use client";

import { useEffect, useRef, useCallback } from "react";
import useSWR from "swr";
import { sessionApi, streamSession } from "@/lib/api";
import { useChatStore } from "@/lib/store";
import type { Message } from "@/types";

export function useChat(sessionId: string | null) {
  const {
    messages,
    streamingText,
    sending,
    setMessages,
    appendMessage,
    setStreamingText,
    appendStreamingText,
    setSending,
    clearForSession,
  } = useChatStore();

  const abortRef = useRef<AbortController | null>(null);

  // Reload messages whenever the active session changes.
  const { mutate } = useSWR(
    sessionId ? `messages:${sessionId}` : null,
    () => sessionApi.getMessages(sessionId!),
    {
      revalidateOnFocus: false,
      onSuccess: (data) => setMessages(data.messages),
    },
  );

  // Clear chat state when session changes.
  useEffect(() => {
    clearForSession();
  }, [sessionId, clearForSession]);

  // Clean up any in-flight stream when unmounting.
  useEffect(() => {
    return () => {
      abortRef.current?.abort();
    };
  }, []);

  const send = useCallback(
    async (text: string, model = "") => {
      if (!sessionId || sending) return;

      setSending(true);
      setStreamingText(null);

      // Show the user's message immediately. The real persisted row replaces
      // this when we mutate() from the DB at the end.
      const optimistic: Message = {
        id: `tmp-${crypto.randomUUID()}`,
        session_id: sessionId,
        user_id: "",
        role: "user",
        content: text,
        model: model || null,
        citations: null,
        created_at: new Date().toISOString(),
      };
      appendMessage(optimistic);

      let finalMessage: Message | null = null;

      try {
        // 1. POST the message FIRST, then open the stream. This order is
        //    deliberate (it is what the working main branch does):
        //    - The worker's reply only arrives seconds later (after the LLM
        //      call), so there is no real race with the subscription.
        //    - The AbortController is created AFTER this await. If it were
        //      created before, React Strict Mode's mount -> cleanup -> remount
        //      would fire the unmount cleanup and abort the controller before
        //      the stream even opens, producing "BodyStreamBuffer was aborted"
        //      and a silently empty reply.
        await sessionApi.sendMessage(sessionId, text, model);

        abortRef.current?.abort();
        const ctrl = new AbortController();
        abortRef.current = ctrl;

        // 2. Open the stream and consume until the final event.
        for await (const event of streamSession(sessionId, ctrl.signal)) {
          if (event.type === "text_delta") {
            // The worker publishes deltas under the "text" field.
            appendStreamingText(event.text ?? "");
          } else if (event.type === "final") {
            finalMessage = {
              id: event.id ?? crypto.randomUUID(),
              session_id: sessionId,
              user_id: event.user_id ?? "",
              role: "assistant",
              content: event.text ?? "",
              model: event.model ?? null,
              citations: event.citations ?? null,
              created_at: event.created_at ?? new Date().toISOString(),
            };
            break;
          } else if (event.type === "error") {
            throw new Error(event.text ?? "Stream error");
          }
          // stream_connected / status / tool_call / worker_ready are ignored.
        }

        // The backend saves the assistant message BEFORE yielding the final
        // event, so the DB row exists by the time we get here. Calling mutate()
        // now pulls the persisted messages and replaces the in-memory state,
        // which means a refresh will always show the full conversation.
        setStreamingText(null);
        if (finalMessage) appendMessage(finalMessage);
        await mutate();
      } catch (err) {
        if ((err as Error).name !== "AbortError") {
          setStreamingText(null);
          console.error("Chat error:", err);
        }
      } finally {
        // Close the stream connection so the backend drops its subscription.
        abortRef.current?.abort();
        setSending(false);
      }
    },
    [
      sessionId,
      sending,
      mutate,
      setSending,
      setStreamingText,
      appendMessage,
      appendStreamingText,
    ],
  );

  return { messages, streamingText, sending, send };
}
