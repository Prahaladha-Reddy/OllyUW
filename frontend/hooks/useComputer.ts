"use client";

import useSWR from "swr";
import { computerApi } from "@/lib/api";
import { useComputerStore } from "@/lib/store";
import { useEffect, useCallback } from "react";

export function useComputer() {
  const { computer, loading, error, setComputer, setLoading, setError } = useComputerStore();

  const { data, mutate } = useSWR("computer", () => computerApi.get(), {
    revalidateOnFocus: false,
    refreshInterval: (data) => {
      // Poll faster while starting so we catch the transition to running quickly.
      const state = data?.computer?.runtime_state;
      return state === "starting" ? 2000 : 10000;
    },
  });

  useEffect(() => {
    if (data?.computer) setComputer(data.computer);
  }, [data, setComputer]);

  const run = useCallback(
    async (action: () => Promise<{ computer: typeof computer }>) => {
      setLoading(true);
      setError(null);
      try {
        const result = await action();
        if (result?.computer) setComputer(result.computer);
        await mutate();
      } catch (e) {
        setError(e instanceof Error ? e.message : "Unknown error");
      } finally {
        setLoading(false);
      }
    },
    [setComputer, setLoading, setError, mutate],
  );

  // Resume an idle-paused sandbox and refresh the desktop URL. Used on load.
  const connect = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await computerApi.connect();
      if (result?.computer) setComputer(result.computer);
      await mutate();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to reconnect");
    } finally {
      setLoading(false);
    }
  }, [setComputer, setLoading, setError, mutate]);

  // Best-effort idle-timeout reset. Silent: never touches loading/error.
  const keepalive = useCallback(async () => {
    try {
      await computerApi.keepalive();
    } catch {
      // Ignored: next reconnect() will resume the sandbox if it paused.
    }
  }, []);

  return {
    computer,
    loading,
    error,
    connect,
    keepalive,
    start: () => run(computerApi.start),
    pause: () => run(computerApi.pause),
    powerOff: () => run(computerApi.powerOff),
    snapshot: () => run(computerApi.snapshot),
    applyMacLook: useCallback(async () => {
      setLoading(true);
      try {
        await computerApi.applyMacLook();
        await mutate();
      } catch (e) {
        setError(e instanceof Error ? e.message : "Mac look failed");
      } finally {
        setLoading(false);
      }
    }, [setLoading, setError, mutate]),
    refetch: mutate,
  };
}
