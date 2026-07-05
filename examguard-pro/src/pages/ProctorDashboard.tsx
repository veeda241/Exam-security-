import { useQuery } from '@tanstack/react-query';
import { sessionsApi } from '../api/client';
import { SessionCard } from '../components/dashboard/SessionCard';
import { useSessionStore } from '../store/sessionStore';
import { useSocket } from '../context/SocketContext';
import { useEffect } from 'react';

export function ProctorDashboard() {
  const { subscribe } = useSocket();
  const connectionStatus = useSessionStore((s) => s.connectionStatus);

  const { data: sessions = [], isLoading } = useQuery({
    queryKey: ['sessions', 'active'],
    queryFn: () => sessionsApi.list({ status_filter: 'active' }).then((r) => r.data),
    refetchInterval: 30000,
  });

  useEffect(() => {
    sessions.forEach((s) => subscribe(s.id));
  }, [sessions, subscribe]);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-slate-900">Live Sessions</h1>
        <span className="text-xs text-slate-500 capitalize">WS: {connectionStatus}</span>
      </div>

      {isLoading ? (
        <p className="text-slate-500">Loading sessions…</p>
      ) : sessions.length === 0 ? (
        <p className="text-slate-500">No active sessions.</p>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {sessions.map((session) => (
            <SessionCard key={session.id} session={session} />
          ))}
        </div>
      )}
    </div>
  );
}
