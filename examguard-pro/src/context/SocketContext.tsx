import { createContext, useContext, useEffect, useRef, useCallback, ReactNode } from 'react';
import { config } from '../config';
import { useSessionStore } from '../store/sessionStore';

interface SocketContextValue {
  subscribe: (sessionId: string) => void;
  unsubscribe: (sessionId: string) => void;
  connectionStatus: string;
}

const SocketContext = createContext<SocketContextValue | null>(null);

export function SocketProvider({ children }: { children: ReactNode }) {
  const wsRef = useRef<WebSocket | null>(null);
  const subscribedRef = useRef<Set<string>>(new Set());
  const { setConnectionStatus, upsertSessionRisk, addEvent, setSessionStatus, connectionStatus } =
    useSessionStore();

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return;

    setConnectionStatus('connecting');
    const ws = new WebSocket(config.wsUrl);
    wsRef.current = ws;

    ws.onopen = () => {
      setConnectionStatus('connected');
      subscribedRef.current.forEach((sessionId) => {
        ws.send(JSON.stringify({ type: 'subscribe', session_id: sessionId }));
      });
    };

    ws.onmessage = (ev) => {
      try {
        const msg = JSON.parse(ev.data);
        const sessionId = msg.session_id;
        if (!sessionId) return;

        if (msg.type === 'event' && msg.event) {
          addEvent(sessionId, msg.event);
        } else if (msg.type === 'risk_update') {
          upsertSessionRisk(sessionId, msg.score, msg.level);
        } else if (msg.type === 'session_status') {
          setSessionStatus(sessionId, msg.status);
        }
      } catch {
        // ignore malformed messages
      }
    };

    ws.onclose = () => {
      setConnectionStatus('disconnected');
      setTimeout(connect, 3000);
    };

    ws.onerror = () => ws.close();
  }, [addEvent, setConnectionStatus, setSessionStatus, upsertSessionRisk]);

  useEffect(() => {
    connect();
    const ping = setInterval(() => {
      if (wsRef.current?.readyState === WebSocket.OPEN) {
        wsRef.current.send(JSON.stringify({ type: 'ping' }));
      }
    }, 20000);
    return () => {
      clearInterval(ping);
      wsRef.current?.close();
    };
  }, [connect]);

  const subscribe = useCallback((sessionId: string) => {
    subscribedRef.current.add(sessionId);
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: 'subscribe', session_id: sessionId }));
    }
  }, []);

  const unsubscribe = useCallback((sessionId: string) => {
    subscribedRef.current.delete(sessionId);
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: 'unsubscribe', session_id: sessionId }));
    }
  }, []);

  return (
    <SocketContext.Provider value={{ subscribe, unsubscribe, connectionStatus }}>
      {children}
    </SocketContext.Provider>
  );
}

export function useSocket() {
  const ctx = useContext(SocketContext);
  if (!ctx) throw new Error('useSocket must be used within SocketProvider');
  return ctx;
}

export function useSessionSocket(sessionId: string | undefined) {
  const { subscribe, unsubscribe } = useSocket();
  useEffect(() => {
    if (!sessionId) return;
    subscribe(sessionId);
    return () => unsubscribe(sessionId);
  }, [sessionId, subscribe, unsubscribe]);
}
