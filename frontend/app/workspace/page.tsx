"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/hooks/useAuth";
import WorkspaceShell from "@/components/workspace/WorkspaceShell";

export default function WorkspacePage() {
  const { user, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!loading && !user) router.replace("/auth");
  }, [user, loading, router]);

  if (loading) {
    return (
      <div
        style={{
          height: "100dvh",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          backgroundColor: "#fbfbfa",
        }}
      >
        <span style={{ fontSize: 13, color: "#787774" }}>Loading...</span>
      </div>
    );
  }

  if (!user) return null;

  return <WorkspaceShell />;
}
