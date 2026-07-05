import { create } from 'zustand';

export interface LiveEvent {
  id?: string;
  session_id: string;
  type: string;
  payload?: Record<string, unknown>;
  weight?: number;
  created_at?: string;
}

interface SessionStore {
  connectionStatus: 'connecting' | 'connected' | 'disconnected';
  sessions: Record<string, { risk_score: number; risk_level: string; status?: string }>;
  events: Record<string, LiveEvent[]>;
  setConnectionStatus: (status: SessionStore['connectionStatus']) => void;
  upsertSessionRisk: (sessionId: string, score: number, level: string) => void;
  addEvent: (sessionId: string, event: LiveEvent) => void;
  setSessionStatus: (sessionId: string, status: string) => void;
  clearSession: (sessionId: string) => void;
}

export const useSessionStore = create<SessionStore>((set) => ({
  connectionStatus: 'disconnected',
  sessions: {},
  events: {},

  setConnectionStatus: (connectionStatus) => set({ connectionStatus }),

  upsertSessionRisk: (sessionId, risk_score, risk_level) =>
    set((state) => ({
      sessions: {
        ...state.sessions,
        [sessionId]: { ...state.sessions[sessionId], risk_score, risk_level },
      },
    })),

  addEvent: (sessionId, event) =>
    set((state) => ({
      events: {
        ...state.events,
        [sessionId]: [...(state.events[sessionId] || []), event].slice(-200),
      },
    })),

  setSessionStatus: (sessionId, status) =>
    set((state) => ({
      sessions: {
        ...state.sessions,
        [sessionId]: { ...state.sessions[sessionId], risk_score: state.sessions[sessionId]?.risk_score ?? 0, risk_level: state.sessions[sessionId]?.risk_level ?? 'safe', status },
      },
    })),

  clearSession: (sessionId) =>
    set((state) => {
      const { [sessionId]: _s, ...sessions } = state.sessions;
      const { [sessionId]: _e, ...events } = state.events;
      return { sessions, events };
    }),
}));
