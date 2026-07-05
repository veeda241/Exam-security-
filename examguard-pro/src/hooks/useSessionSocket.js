import { useEffect } from 'react';
import { useSocket } from '../context/SocketContext';

export function useSessionSocket(sessionId) {
  const { subscribe, unsubscribe } = useSocket();

  useEffect(() => {
    if (!sessionId) return;
    subscribe(sessionId);
    return () => unsubscribe(sessionId);
  }, [sessionId, subscribe, unsubscribe]);
}
