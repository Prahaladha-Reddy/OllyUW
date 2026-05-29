"use client";

import { useState, useCallback } from "react";
import useSWR from "swr";
import { computerApi } from "@/lib/api";

export function useWorkspaceFolders(enabled: boolean) {
  const { data, isLoading, mutate } = useSWR(
    enabled ? "workspace/folders" : null,
    () => computerApi.workspace.listFolders(),
    { revalidateOnFocus: false },
  );

  return { folders: data?.folders ?? [], isLoading, refetch: mutate };
}

export function useUpload() {
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const upload = useCallback(async (files: File[], destPath: string): Promise<boolean> => {
    setUploading(true);
    setError(null);
    try {
      await computerApi.workspace.upload(files, destPath);
      return true;
    } catch (e) {
      setError(e instanceof Error ? e.message : "Upload failed");
      return false;
    } finally {
      setUploading(false);
    }
  }, []);

  return { upload, uploading, error };
}
