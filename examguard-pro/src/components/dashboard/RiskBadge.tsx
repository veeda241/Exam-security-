import { riskColor } from '../../hooks/useRiskColor';

interface RiskBadgeProps {
  level: string;
  score?: number;
}

export function RiskBadge({ level, score }: RiskBadgeProps) {
  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium border ${riskColor(level)}`}>
      {level}
      {score !== undefined && <span className="opacity-70">({Math.round(score)})</span>}
    </span>
  );
}
