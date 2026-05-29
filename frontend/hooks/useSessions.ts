"use client";

import useSWR from "swr";
import { sessionApi } from "@/lib/api";
import { useSessionStore } from "@/lib/store";
import { useEffect, useCallback } from "react";

export function useSessions() {
  const { sessions, activeId, setSessions, setActiveId, addSession, removeSession } =
    useSessionStore();

  const { mutate } = useSWR("sessions", () => sessionApi.list(), {
    revalidateOnFocus: false,
    onSuccess: (data) => {
      setSessions(data.sessions);
      // Auto-activate first session when nothing is selected.
      if (!activeId && data.sessions.length > 0) {
        setActiveId(data.sessions[0]?.id ?? null);
      }
    },
  });

  const create = useCallback(
    async (title = "New session") => {
      const { session } = await sessionApi.create(title);
      addSession(session);
      setActiveId(session.id);
      return session;
    },
    [addSession, setActiveId],
  );

  const remove = useCallback(
    async (id: string) => {
      await sessionApi.delete(id);
      removeSession(id);
    },
    [removeSession],
  );

  return { sessions, activeId, setActiveId, create, remove, refetch: mutate };
}
