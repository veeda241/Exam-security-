import React from 'react';
import { ArrowUpRight, Bot, ShieldAlert } from 'lucide-react';
import { RiskMeter } from './RiskMeter';

type AgentVerdictCardProps = {
  verdict: any;
};

function formatTimestamp(value: any) {
  if (!value) return 'Just now';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return 'Just now';
  return date.toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' });
}

function niceLabel(value: any) {
  return String(value || 'unknown').replace(/_/g, ' ');
}

export function AgentVerdictCard({ verdict }: AgentVerdictCardProps) {
  const agentDetails = verdict?.agent_details || {};
  const agentEntries = Object.entries(agentDetails);
  const riskLevel = niceLabel(verdict?.risk_level);
  const action = niceLabel(verdict?.recommended_action);

  return (
    <article className="rounded-2xl border border-slate-200 bg-slate-50/80 p-5 shadow-sm hover:shadow-md transition-shadow">
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <span className="inline-flex items-center gap-1 rounded-full bg-indigo-50 px-2.5 py-1 text-[11px] font-semibold uppercase tracking-wide text-indigo-700">
              <Bot className="h-3.5 w-3.5" />
              {niceLabel(verdict?.primary_agent)}
            </span>
            <span className={`inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-[11px] font-semibold uppercase tracking-wide ${verdict?.risk_level === 'suspicious' ? 'bg-rose-50 text-rose-700' : verdict?.risk_level === 'review' ? 'bg-amber-50 text-amber-700' : 'bg-emerald-50 text-emerald-700'}`}>
              <ShieldAlert className="h-3.5 w-3.5" />
              {riskLevel}
            </span>
          </div>

          <h3 className="mt-3 text-sm font-semibold text-slate-900 truncate">
            {verdict?.domain || verdict?.url || 'Site verdict'}
          </h3>
          <p className="mt-1 text-xs text-slate-500">
            {verdict?.summary || 'Live agent consensus returned no summary.'}
          </p>
        </div>

        <div className="text-right shrink-0">
          <div className="text-2xl font-bold text-slate-900">{Math.round(Number(verdict?.risk_score || 0))}</div>
          <div className="text-[11px] uppercase tracking-wide text-slate-400">risk score</div>
          <div className="mt-2 inline-flex items-center gap-1 rounded-full bg-slate-100 px-2 py-1 text-[11px] font-medium text-slate-500">
            <ArrowUpRight className="h-3.5 w-3.5" />
            {action}
          </div>
        </div>
      </div>

      <div className="mt-4">
        <RiskMeter
          riskScore={verdict?.risk_score}
          effortScore={verdict?.effort_score}
          decayFactor={verdict?.decay_factor}
        />
      </div>

      <div className="mt-4 grid grid-cols-2 gap-3 text-xs text-slate-600">
        <div className="rounded-xl bg-white px-3 py-2 border border-slate-200">
          <div className="text-[10px] uppercase tracking-wide text-slate-400">Consensus</div>
          <div className="mt-1 font-semibold text-slate-900">{niceLabel(verdict?.consensus)}</div>
        </div>
        <div className="rounded-xl bg-white px-3 py-2 border border-slate-200">
          <div className="text-[10px] uppercase tracking-wide text-slate-400">Confidence</div>
          <div className="mt-1 font-semibold text-slate-900">{Math.round(Number(verdict?.confidence || 0) * 100)}%</div>
        </div>
        <div className="rounded-xl bg-white px-3 py-2 border border-slate-200">
          <div className="text-[10px] uppercase tracking-wide text-slate-400">YouTube intent</div>
          <div className="mt-1 font-semibold text-slate-900">{niceLabel(verdict?.youtube_intent)}</div>
        </div>
        <div className="rounded-xl bg-white px-3 py-2 border border-slate-200">
          <div className="text-[10px] uppercase tracking-wide text-slate-400">Generated</div>
          <div className="mt-1 font-semibold text-slate-900">{formatTimestamp(verdict?.generated_at)}</div>
        </div>
      </div>

      <div className="mt-4 flex flex-wrap gap-2">
        <span className="rounded-full bg-slate-100 px-2.5 py-1 text-[11px] font-medium text-slate-600">
          {niceLabel(verdict?.site_category)}
        </span>
        <span className="rounded-full bg-slate-100 px-2.5 py-1 text-[11px] font-medium text-slate-600">
          {niceLabel(verdict?.primary_agent)}
        </span>
        <span className="rounded-full bg-slate-100 px-2.5 py-1 text-[11px] font-medium text-slate-600">
          action: {action}
        </span>
      </div>

      {agentEntries.length > 0 && (
        <div className="mt-4 space-y-2">
          <div className="text-[10px] font-semibold uppercase tracking-wide text-slate-400">Agent details</div>
          <div className="space-y-2">
            {agentEntries.map(([agentName, detail]: any) => (
              <div key={agentName} className="rounded-xl bg-white border border-slate-200 px-3 py-2">
                <div className="flex items-center justify-between gap-3">
                  <div>
                    <div className="text-sm font-semibold text-slate-900">{niceLabel(detail?.label || agentName)}</div>
                    <div className="text-xs text-slate-500">{niceLabel(detail?.category || detail?.agent_name || agentName)}</div>
                  </div>
                  <div className="text-right text-xs text-slate-500">
                    <div>risk {Math.round(Number(detail?.risk_score || 0))}</div>
                    <div>confidence {Math.round(Number(detail?.confidence || 0) * 100)}%</div>
                  </div>
                </div>
                <p className="mt-2 text-xs text-slate-500">{detail?.reason || 'No reason returned.'}</p>
              </div>
            ))}
          </div>
        </div>
      )}
    </article>
  );
}