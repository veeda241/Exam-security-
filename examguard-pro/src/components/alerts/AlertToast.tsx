import { useSessionStore } from '../../store/sessionStore';

export function AlertToast() {
  const events = useSessionStore((s) => s.events);
  const latest = Object.values(events).flat().slice(-1)[0];

  if (!latest || !latest.weight || latest.weight < 20) return null;

  return (
    <div className="fixed bottom-20 right-4 z-50 max-w-sm p-4 bg-red-50 border border-red-200 rounded-xl shadow-lg">
      <p className="text-sm font-semibold text-red-800">Risk alert</p>
      <p className="text-xs text-red-600 mt-1">{latest.type} (+{latest.weight})</p>
    </div>
  );
}
