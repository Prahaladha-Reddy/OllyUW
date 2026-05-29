import type { RuntimeState } from "@/types";

export function cn(...classes: (string | false | undefined | null)[]): string {
  return classes.filter(Boolean).join(" ");
}

export function timeAgo(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const m = Math.floor(diff / 60_000);
  const h = Math.floor(diff / 3_600_000);
  const d = Math.floor(diff / 86_400_000);
  if (m < 1) return "just now";
  if (m < 60) return `${m}m ago`;
  if (h < 24) return `${h}h ago`;
  if (d < 7) return `${d}d ago`;
  return new Date(iso).toLocaleDateString();
}

export function runtimeBadge(state: RuntimeState): { label: string; bg: string; color: string } {
  switch (state) {
    case "running":
      return { label: "Running", bg: "#EDF3EC", color: "#346538" };
    case "starting":
      return { label: "Starting", bg: "#E1F3FE", color: "#1F6C9F" };
    case "paused":
      return { label: "Paused", bg: "#FBF3DB", color: "#956400" };
    case "error":
      return { label: "Error", bg: "#FDEBEC", color: "#9F2F2D" };
    case "stopped":
    default:
      return { label: "Offline", bg: "#F0F0EF", color: "#787774" };
  }
}

export function folderName(path: string): string {
  if (!path) return "Root";
  const parts = path.split("/").filter(Boolean);
  return parts[parts.length - 1] ?? "Root";
}

export function folderDepth(path: string): number {
  if (!path) return 0;
  return path.split("/").filter(Boolean).length;
}
