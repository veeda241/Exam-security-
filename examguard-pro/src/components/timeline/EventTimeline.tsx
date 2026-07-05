import type { SessionEvent } from '../../api/client';
import { useSessionStore } from '../../store/sessionStore';

interface EventTimelineProps {
  sessionId: string;
  settledEvents?: SessionEvent[];
}

export function EventTimeline({ sessionId, settledEvents = [] }: EventTimelineProps) {
  const liveEvents = useSessionStore((s) => s.events[sessionId] || []);
  const merged = [...settledEvents, ...liveEvents].slice(-50).reverse();

  return (
    <div className="space-y-2">
      {merged.length === 0 && (
        <p className="text-sm text-slate-500">No events yet.</p>
      )}
      {merged.map((ev, i) => (
        <div key={ev.id || i} className="flex items-start gap-3 p-3 bg-white rounded-lg border border-slate-100">
          <span className="text-xs text-slate-400 whitespace-nowrap">
            {ev.created_at ? new Date(ev.created_at).toLocaleTimeString() : '—'}
          </span>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium text-slate-800">{ev.type}</p>
            {ev.weight !== undefined && ev.weight > 0 && (
              <p className="text-xs text-slate-500">Weight: +{ev.weight}</p>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}
