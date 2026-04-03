import { useEffect, useState, useRef, useCallback } from 'react';
import { config } from '../config';

// Singleton WebSocket manager - persists across React StrictMode re-renders
class WebSocketManager {
  private ws: WebSocket | null = null;
  private url: string;
  private subscribers: Set<(data: any) => void> = new Set();
  private statusSubscribers: Set<(connected: boolean) => void> = new Set();
  private reconnectAttempts = 0;
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private connecting = false;
  private subscribedRooms: Set<string> = new Set();
  
  private MAX_RECONNECT_ATTEMPTS = 5;

  constructor(url: string) {
    this.url = url;
  }

  connect() {
    if (this.ws?.readyState === WebSocket.OPEN || this.ws?.readyState === WebSocket.CONNECTING || this.connecting) {
      return;
    }

    this.connecting = true;
    
    try {
      this.ws = new WebSocket(this.url);

      this.ws.onopen = () => {
        this.connecting = false;
        this.reconnectAttempts = 0;
        console.log(`[WS] Connected to ${this.url}`);
        this.notifyStatus(true);
        
        // Re-subscribe to all rooms
        this.subscribedRooms.forEach(room => {
          this.ws?.send(`subscribe:${room}`);
        });
      };

      this.ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          const msgType = data.event_type || data.type;
          const ignoredTypes = ['connection', 'heartbeat', 'pong', 'subscribed'];
          if (msgType && !ignoredTypes.includes(msgType)) {
            this.subscribers.forEach(cb => cb(data));
          }
        } catch {
          // ignore non-JSON
        }
      };

      this.ws.onclose = (event) => {
        this.connecting = false;
        this.notifyStatus(false);
        
        if (event.code !== 1000 && event.code !== 1001 && this.reconnectAttempts < this.MAX_RECONNECT_ATTEMPTS) {
          const delay = Math.min(2000 * Math.pow(2, this.reconnectAttempts), 30000);
          this.reconnectAttempts++;
          this.reconnectTimer = setTimeout(() => this.connect(), delay);
        }
      };

      this.ws.onerror = () => {
        this.connecting = false;
      };
    } catch (err) {
      this.connecting = false;
      console.warn('[WS] Failed to create WebSocket:', err);
    }
  }

  subscribe(callback: (data: any) => void): () => void {
    this.subscribers.add(callback);
    this.connect();
    return () => {
      this.subscribers.delete(callback);
    };
  }

  subscribeStatus(callback: (connected: boolean) => void): () => void {
    this.statusSubscribers.add(callback);
    // Immediately notify current status
    callback(this.ws?.readyState === WebSocket.OPEN);
    return () => {
      this.statusSubscribers.delete(callback);
    };
  }

  subscribeRoom(roomId: string) {
    this.subscribedRooms.add(roomId);
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(`subscribe:${roomId}`);
      console.log(`[WS] Subscribed to room: ${roomId}`);
    }
  }

  unsubscribeRoom(roomId: string) {
    this.subscribedRooms.delete(roomId);
  }

  send(msg: string) {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(msg);
    }
  }

  private notifyStatus(connected: boolean) {
    this.statusSubscribers.forEach(cb => cb(connected));
  }

  disconnect() {
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
    if (this.ws) {
      this.ws.close(1000, 'Manager disconnect');
      this.ws = null;
    }
    this.subscribedRooms.clear();
  }
}

// Global singleton instances
const dashboardWs = new WebSocketManager(`${config.wsUrl}/dashboard`);

export const useWebSocket = (roomId?: string, onMessage?: (data: any) => void) => {
  const [messages, setMessages] = useState<any[]>([]);
  const [isConnected, setIsConnected] = useState(false);

  // Subscribe to messages
  useEffect(() => {
    if (!onMessage) return;
    
    const handleMessage = (data: any) => {
      console.log('[WS] Received:', data.event_type || data.type, data.student_id || '');
      setMessages(prev => [data, ...prev].slice(0, 50));
      onMessage(data);
    };

    const unsubscribe = dashboardWs.subscribe(handleMessage);
    return unsubscribe;
  }, [onMessage]);

  // Subscribe to connection status
  useEffect(() => {
    const unsubscribe = dashboardWs.subscribeStatus(setIsConnected);
    return unsubscribe;
  }, []);

  // Subscribe to room
  useEffect(() => {
    if (!roomId) return;
    const cleanRoomId = roomId.startsWith('/') ? roomId.slice(1) : roomId;
    if (cleanRoomId) {
      dashboardWs.subscribeRoom(cleanRoomId);
    }
    return () => {
      if (cleanRoomId) {
        dashboardWs.unsubscribeRoom(cleanRoomId);
      }
    };
  }, [roomId]);

  const sendMessage = useCallback((msg: string) => {
    dashboardWs.send(msg);
  }, []);

  return { messages, isConnected, sendMessage };
};
