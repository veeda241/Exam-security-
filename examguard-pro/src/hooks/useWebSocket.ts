import { useEffect, useRef, useCallback, useState } from 'react';
import { config } from '../config';

const MAX_MESSAGES = 200;

export interface WsMessage {
  type?: string;
  event_type?: string;
  session_id?: string;
  student_id?: string;
  url?: string;
  timestamp?: string;
  generated_at?: string;
  alert_level?: string;
  message?: string;
  data?: {
    type?: string;
    event_type?: string;
    message?: string;
    session_id?: string;
    student_id?: string;
    url?: string;
    generated_at?: string;
    [key: string]: unknown;
  };
  [key: string]: unknown;
}

function buildWsUrl(): string {
  return config.wsUrl.replace(/\/$/, '');
}

export const useWebSocket = (
  channel?: string,
  onMessage?: (message: WsMessage) => void,
) => {
  const ws = useRef<WebSocket | null>(null);
  const reconnectTimeout = useRef<number | null>(null);
  const onMessageRef = useRef(onMessage);
  const [messages, setMessages] = useState<WsMessage[]>([]);
  const [isConnected, setIsConnected] = useState(false);

  onMessageRef.current = onMessage;

  const connect = useCallback(() => {
    if (ws.current?.readyState === WebSocket.OPEN) return;

    const url = buildWsUrl();
    ws.current = new WebSocket(url);

    ws.current.onopen = () => {
      setIsConnected(true);
      const sessionId =
        channel && channel !== '/dashboard' && channel !== 'dashboard' ? channel : null;
      if (sessionId) {
        ws.current?.send(JSON.stringify({ type: 'subscribe', session_id: sessionId }));
      }
    };

    ws.current.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data) as WsMessage;
        setMessages((prev) => [data, ...prev].slice(0, MAX_MESSAGES));
        onMessageRef.current?.(data);
      } catch (error) {
        console.error('WebSocket message parse error:', error);
      }
    };

    ws.current.onclose = () => {
      setIsConnected(false);
      reconnectTimeout.current = window.setTimeout(connect, 3000);
    };

    ws.current.onerror = () => {
      ws.current?.close();
    };
  }, [channel]);

  useEffect(() => {
    connect();
    return () => {
      if (reconnectTimeout.current) clearTimeout(reconnectTimeout.current);
      ws.current?.close();
    };
  }, [connect]);

  const sendMessage = useCallback((message: unknown) => {
    if (ws.current?.readyState !== WebSocket.OPEN) return;

    if (typeof message === 'string') {
      ws.current.send(message);
      return;
    }

    ws.current.send(JSON.stringify(message));
  }, []);

  return { messages, sendMessage, isConnected };
};
