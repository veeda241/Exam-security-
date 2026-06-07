import React from 'react';

type RiskMeterProps = {
  riskScore?: number;
  effortScore?: number;
  decayFactor?: number;
};

function clampPercentage(value: number | undefined) {
  const numeric = Number.isFinite(Number(value)) ? Number(value) : 0;
  return Math.max(0, Math.min(100, numeric));
}

export function RiskMeter({ riskScore, effortScore, decayFactor }: RiskMeterProps) {
  const risk = clampPercentage(riskScore);
  const effort = clampPercentage(effortScore);
  const decay = Math.max(0, Math.min(1, Number(decayFactor ?? 0)));

  const riskTone = risk >= 60 ? 'from-rose-500 to-rose-600' : risk >= 30 ? 'from-amber-500 to-amber-600' : 'from-emerald-500 to-emerald-600';
  const effortTone = effort >= 70 ? 'from-emerald-500 to-emerald-600' : effort >= 40 ? 'from-amber-500 to-amber-600' : 'from-rose-500 to-rose-600';

  return (
    <div className="space-y-3">
      <div>
        <div className="flex items-center justify-between text-xs font-semibold text-slate-500 mb-1.5">
          <span>Risk</span>
          <span>{risk.toFixed(0)}%</span>
        </div>
        <div className="h-2 rounded-full bg-slate-100 overflow-hidden">
          <div className={`h-full rounded-full bg-gradient-to-r ${riskTone}`} style={{ width: `${risk}%` }} />
        </div>
      </div>

      <div>
        <div className="flex items-center justify-between text-xs font-semibold text-slate-500 mb-1.5">
          <span>Effort</span>
          <span>{effort.toFixed(0)}%</span>
        </div>
        <div className="h-2 rounded-full bg-slate-100 overflow-hidden">
          <div className={`h-full rounded-full bg-gradient-to-r ${effortTone}`} style={{ width: `${effort}%` }} />
        </div>
      </div>

      <div className="flex items-center justify-between text-[11px] uppercase tracking-wide text-slate-400">
        <span>Decay factor</span>
        <span>{decay.toFixed(2)}</span>
      </div>
    </div>
  );
}