"use client";

import useSWR from "swr";
import { connectionsApi, type ToolkitStatus } from "@/lib/api";

export function useConnections() {
  const { data, error, isLoading, mutate } = useSWR(
    "connections/toolkits/connected",
    () => connectionsApi.listToolkits(true),
    { revalidateOnFocus: false }
  );

  return {
    connected: data?.toolkits ?? [],
    loading: isLoading,
    error: error?.message ?? null,
    refresh: mutate,
  };
}

export function useAllToolkits() {
  const { data, error, isLoading, mutate } = useSWR(
    "connections/toolkits/all",
    () => connectionsApi.listToolkits(false),
    { revalidateOnFocus: false }
  );

  return {
    toolkits: data?.toolkits ?? [],
    loading: isLoading,
    error: error?.message ?? null,
    refresh: mutate,
  };
}

// Open Composio OAuth in a popup and resolve when the user finishes (or closes).
export async function connectApp(
  toolkit: string,
  onSuccess: () => void
): Promise<void> {
  const callbackUrl = `${window.location.origin}/connections/callback`;
  const { redirect_url } = await connectionsApi.connect(toolkit, callbackUrl);

  const popup = window.open(
    redirect_url,
    "composio_oauth",
    "width=560,height=680,left=200,top=100,resizable=yes,scrollbars=yes"
  );

  if (!popup) {
    // Popup blocked — fall back to same-tab redirect.
    window.location.href = redirect_url;
    return;
  }

  const handler = (e: MessageEvent) => {
    if (e.data?.type === "composio_callback") {
      window.removeEventListener("message", handler);
      popup.close();
      onSuccess();
    }
  };
  window.addEventListener("message", handler);

  // Clean up listener if popup is closed without completing auth.
  const poll = setInterval(() => {
    if (popup.closed) {
      clearInterval(poll);
      window.removeEventListener("message", handler);
    }
  }, 500);
}
