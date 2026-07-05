import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts';
import { useSessionStore } from '../../store/sessionStore';

interface RiskScoreChartProps {
  sessionId: string;
}

export function RiskScoreChart({ sessionId }: RiskScoreChartProps) {
  const events = useSessionStore((s) => s.events[sessionId] || []);
  const liveScore = useSessionStore((s) => s.sessions[sessionId]?.risk_score ?? 0);

  const data = events.reduce<{ time: string; score: number }[]>((acc, ev, i) => {
    const prev = acc.length ? acc[acc.length - 1].score : 0;
    acc.push({
      time: ev.created_at ? new Date(ev.created_at).toLocaleTimeString() : `#${i + 1}`,
      score: prev + (ev.weight || 0),
    });
    return acc;
  }, []);

  if (data.length === 0) {
    data.push({ time: 'now', score: liveScore });
  } else {
    data.push({ time: 'live', score: liveScore });
  }

  return (
    <div className="h-48 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data}>
          <XAxis dataKey="time" tick={{ fontSize: 10 }} />
          <YAxis tick={{ fontSize: 10 }} />
          <Tooltip />
          <Line type="monotone" dataKey="score" stroke="#2563eb" strokeWidth={2} dot={false} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
