import { create } from 'zustand';

interface AppState {
  user: any | null;
  sessions: any[];
  activeSessionId: string | null;
  setUser: (user: any) => void;
  setSessions: (sessions: any[]) => void;
  setActiveSessionId: (id: string | null) => void;
  logout: () => void;
}

export const useAppStore = create<AppState>((set) => ({
  user: null,
  sessions: [],
  activeSessionId: null,
  setUser: (user) => set({ user }),
  setSessions: (sessions) => set({ sessions }),
  setActiveSessionId: (id) => set({ activeSessionId: id }),
  logout: () => set({ user: null, activeSessionId: null, sessions: [] }),
}));
