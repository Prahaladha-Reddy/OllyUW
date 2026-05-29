import { create } from "zustand";
import type { Computer, Session, Message } from "@/types";

// ---- Computer store ----

interface ComputerState {
  computer: Computer | null;
  loading: boolean;
  error: string | null;
  setComputer: (c: Computer) => void;
  setLoading: (v: boolean) => void;
  setError: (e: string | null) => void;
}

export const useComputerStore = create<ComputerState>((set) => ({
  computer: null,
  loading: false,
  error: null,
  setComputer: (c) => set({ computer: c, error: null }),
  setLoading: (v) => set({ loading: v }),
  setError: (e) => set({ error: e }),
}));

// ---- Session store ----

interface SessionState {
  sessions: Session[];
  activeId: string | null;
  setSessions: (s: Session[]) => void;
  setActiveId: (id: string | null) => void;
  addSession: (s: Session) => void;
  removeSession: (id: string) => void;
}

export const useSessionStore = create<SessionState>((set) => ({
  sessions: [],
  activeId: null,
  setSessions: (sessions) => set({ sessions }),
  setActiveId: (activeId) => set({ activeId }),
  addSession: (s) => set((state) => ({ sessions: [...state.sessions, s] })),
  removeSession: (id) =>
    set((state) => ({
      sessions: state.sessions.filter((s) => s.id !== id),
      activeId: state.activeId === id ? null : state.activeId,
    })),
}));

// ---- Chat store ----

interface ChatState {
  messages: Message[];
  streamingText: string | null;
  sending: boolean;
  setMessages: (m: Message[]) => void;
  appendMessage: (m: Message) => void;
  setStreamingText: (t: string | null) => void;
  appendStreamingText: (chunk: string) => void;
  setSending: (v: boolean) => void;
  clearForSession: () => void;
}

export const useChatStore = create<ChatState>((set) => ({
  messages: [],
  streamingText: null,
  sending: false,
  setMessages: (messages) => set({ messages }),
  appendMessage: (m) => set((state) => ({ messages: [...state.messages, m] })),
  setStreamingText: (streamingText) => set({ streamingText }),
  appendStreamingText: (chunk) =>
    set((state) => ({ streamingText: (state.streamingText ?? "") + chunk })),
  setSending: (sending) => set({ sending }),
  clearForSession: () => set({ messages: [], streamingText: null, sending: false }),
}));

// ---- UI store ----

interface UIState {
  sidebarOpen: boolean;
  desktopRatio: number;
  uploadModalOpen: boolean;
  // Bumped to force the desktop iframe to remount. A resumed sandbox keeps the
  // same id, so its stream URL is unchanged - without this the iframe would
  // never reload and would keep showing the pre-resume "Failed to connect".
  desktopReloadKey: number;
  setSidebarOpen: (v: boolean) => void;
  setDesktopRatio: (r: number) => void;
  setUploadModalOpen: (v: boolean) => void;
  bumpDesktopReload: () => void;
}

export const useUIStore = create<UIState>((set) => ({
  sidebarOpen: true,
  desktopRatio: 0.55,
  uploadModalOpen: false,
  desktopReloadKey: 0,
  setSidebarOpen: (sidebarOpen) => set({ sidebarOpen }),
  setDesktopRatio: (desktopRatio) => set({ desktopRatio }),
  setUploadModalOpen: (uploadModalOpen) => set({ uploadModalOpen }),
  bumpDesktopReload: () => set((s) => ({ desktopReloadKey: s.desktopReloadKey + 1 })),
}));
