import { create } from 'zustand';

export const useSessionStore = create((set) => ({
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
        [sessionId]: {
          ...state.sessions[sessionId],
          risk_score: state.sessions[sessionId]?.risk_score ?? 0,
          risk_level: state.sessions[sessionId]?.risk_level ?? 'safe',
          status,
        },
      },
    })),

  clearSession: (sessionId) =>
    set((state) => {
      const { [sessionId]: _s, ...sessions } = state.sessions;
      const { [sessionId]: _e, ...events } = state.events;
      return { sessions, events };
    }),
}));
