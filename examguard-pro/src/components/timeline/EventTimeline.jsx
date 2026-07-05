import { useSessionStore } from '../../store/sessionStore.js';

export function EventTimeline({ sessionId, settledEvents = [] }) {
  const liveEvents = useSessionStore((s) => s.events[sessionId] || []);
  const merged = [...settledEvents, ...liveEvents].slice(-50).reverse();

  return (
    <div className="space-y-2">
      {merged.length === 0 && <p className="text-sm text-slate-500">No events yet.</p>}
      {merged.map((ev, i) => (
        <div key={ev.id || i} className="flex gap-3 p-3 bg-white rounded-lg border">
          <span className="text-xs text-slate-400">
            {ev.created_at ? new Date(ev.created_at).toLocaleTimeString() : '—'}
          </span>
          <div className="flex-1">
            <p className="text-sm font-medium">{ev.type}</p>
            {ev.weight > 0 && <p className="text-xs text-slate-500">Weight: +{ev.weight}</p>}
          </div>
        </div>
      ))}
    </div>
  );
}
