import { useEffect, useState } from 'react';
import { config } from '../config';

export const useWebSocket = (endpoint = '/dashboard') => {
  const [messages, setMessages] = useState<any[]>([]);
  const [isConnected, setIsConnected] = useState(false);

  useEffect(() => {
    const ws = new WebSocket(`${config.wsUrl}${endpoint}`);
    
    ws.onopen = () => {
      console.log(`[WS] Connected to ${config.wsUrl}${endpoint}`);
      setIsConnected(true);
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        // Only store real suspicious activity alerts, not system messages
        const ignoredTypes = ['connection', 'heartbeat', 'risk_score_update', 'session_started', 'session_ended', 'student_joined', 'student_left'];
        const msgType = data.event_type || data.type;
        if (msgType && !ignoredTypes.includes(msgType)) {
          setMessages(prev => [data, ...prev].slice(0, 50));
        }
      } catch (e) {
        console.warn("[WS] Non-JSON message:", event.data);
      }
    };

    ws.onclose = () => {
      console.log('[WS] Disconnected');
      setIsConnected(false);
    };

    return () => ws.close();
  }, [endpoint]);

  return { messages, isConnected };
};
