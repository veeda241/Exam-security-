import { Link } from 'react-router-dom';
import { RiskBadge } from './RiskBadge';
import type { Session } from '../../api/client';
import { useSessionStore } from '../../store/sessionStore';

interface SessionCardProps {
  session: Session;
}

export function SessionCard({ session }: SessionCardProps) {
  const live = useSessionStore((s) => s.sessions[session.id]);
  const score = live?.risk_score ?? session.risk_score;
  const level = live?.risk_level ?? session.risk_level;

  return (
    <Link
      to={`/sessions/${session.id}`}
      className="block p-4 bg-white rounded-xl border border-slate-200 hover:border-blue-300 hover:shadow-sm transition-all"
    >
      <div className="flex items-center justify-between mb-2">
        <span className="text-sm font-medium text-slate-700 truncate">{session.id.slice(0, 8)}…</span>
        <RiskBadge level={level} score={score} />
      </div>
      <p className="text-xs text-slate-500 capitalize">{session.status}</p>
    </Link>
  );
}
