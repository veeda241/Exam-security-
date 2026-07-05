import { useParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { sessionsApi, eventsApi } from '../api/client';
import { useSessionSocket } from '../context/SocketContext';
import { useSessionStore } from '../store/sessionStore';
import { RiskBadge } from '../components/dashboard/RiskBadge';
import { EventTimeline } from '../components/timeline/EventTimeline';
import { RiskScoreChart } from '../components/charts/RiskScoreChart';

export function SessionDetailPage() {
  const { sessionId } = useParams<{ sessionId: string }>();
  useSessionSocket(sessionId);

  const { data: session, isLoading } = useQuery({
    queryKey: ['session', sessionId],
    queryFn: () => sessionsApi.get(sessionId!).then((r) => r.data),
    enabled: !!sessionId,
  });

  const { data: settledEvents = [] } = useQuery({
    queryKey: ['events', sessionId],
    queryFn: () => eventsApi.list(sessionId!).then((r) => r.data),
    enabled: !!sessionId,
  });

  const live = useSessionStore((s) => (sessionId ? s.sessions[sessionId] : undefined));

  if (isLoading || !session) {
    return <p className="text-slate-500">Loading session…</p>;
  }

  const score = live?.risk_score ?? session.risk_score;
  const level = live?.risk_level ?? session.risk_level;

  return (
    <div className="space-y-6 max-w-4xl">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-slate-900">Session Detail</h1>
        <RiskBadge level={level} score={score} />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="p-4 bg-white rounded-xl border border-slate-200">
          <h2 className="text-sm font-semibold text-slate-700 mb-3">Risk Score</h2>
          <RiskScoreChart sessionId={sessionId!} />
        </div>
        <div className="p-4 bg-white rounded-xl border border-slate-200">
          <h2 className="text-sm font-semibold text-slate-700 mb-3">Info</h2>
          <dl className="text-sm space-y-1">
            <div><dt className="text-slate-500 inline">Status: </dt><dd className="inline capitalize">{session.status}</dd></div>
            <div><dt className="text-slate-500 inline">Started: </dt><dd className="inline">{session.started_at ? new Date(session.started_at).toLocaleString() : '—'}</dd></div>
          </dl>
        </div>
      </div>

      <div>
        <h2 className="text-sm font-semibold text-slate-700 mb-3">Event Timeline</h2>
        <EventTimeline sessionId={sessionId!} settledEvents={settledEvents} />
      </div>
    </div>
  );
}
