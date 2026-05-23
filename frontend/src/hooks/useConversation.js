import { useCallback, useEffect, useState } from "react";
import { getConversation, listMessages } from "../lib/api.js";

export function useConversation(session, projectId, conversationId) {
  const [conversation, setConversation] = useState(null);
  const [messages, setMessages] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");

  const refresh = useCallback(async () => {
    if (!session || !projectId || !conversationId) {
      setConversation(null);
      setMessages([]);
      return;
    }

    setIsLoading(true);
    setError("");

    try {
      const [conv, msgResponse] = await Promise.all([
        getConversation(session, projectId, conversationId),
        listMessages(session, projectId, conversationId),
      ]);
      setConversation(conv);
      setMessages(msgResponse.messages || []);
    } catch (requestError) {
      setError(requestError.message || "Could not load conversation.");
    } finally {
      setIsLoading(false);
    }
  }, [conversationId, projectId, session]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  return { conversation, messages, error, isLoading, refresh };
}
