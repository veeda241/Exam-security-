import { useEffect, useRef, useCallback } from 'react';
import { WS_URL, CONFIG } from '../config';

export function useWebSocket(onMessage) {
  const wsRef = useRef(null);
  const reconnectAttempts = useRef(0);
  const isConnected = useRef(false);

  const connect = useCallback(() => {
    try {
      const ws = new WebSocket(WS_URL);
      wsRef.current = ws;

      ws.onopen = () => {
        console.log('[WS] Connected');
        isConnected.current = true;
        reconnectAttempts.current = 0;
        onMessage({ type: '__connection', connected: true });
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          onMessage(data);
        } catch (e) {
          console.error('[WS] Parse error:', e);
        }
      };

      ws.onclose = () => {
        console.log('[WS] Disconnected');
        isConnected.current = false;
        onMessage({ type: '__connection', connected: false });
        attemptReconnect();
      };

      ws.onerror = (error) => {
        console.error('[WS] Error:', error);
      };
    } catch (e) {
      console.error('[WS] Connection failed:', e);
      onMessage({ type: '__connection', connected: false });
    }
  }, [onMessage]);

  const attemptReconnect = useCallback(() => {
    if (reconnectAttempts.current < CONFIG.MAX_RECONNECT_ATTEMPTS) {
      reconnectAttempts.current++;
      const delay = Math.min(1000 * Math.pow(2, reconnectAttempts.current), 30000);
      setTimeout(connect, delay);
    }
  }, [connect]);

  useEffect(() => {
    connect();
    // Heartbeat
    const heartbeat = setInterval(() => {
      if (wsRef.current?.readyState === WebSocket.OPEN) {
        wsRef.current.send('ping');
      }
    }, 25000);

    return () => {
      clearInterval(heartbeat);
      wsRef.current?.close();
    };
  }, [connect]);

  return wsRef;
}
