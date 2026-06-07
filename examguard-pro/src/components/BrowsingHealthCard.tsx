import { Globe, MapPin, Target, Activity } from 'lucide-react';

type BrowsingHealthCardProps = {
  browsing?: any;
};

function formatHost(url?: string) {
  if (!url) return 'unknown';
  try {
    return new URL(url).hostname.replace(/^www\./, '').substring(0, 28);
  } catch {
    return String(url).replace(/^https?:\/\//, '').substring(0, 28);
  }
}

function clamp(value: number) {
  return Math.max(0, Math.min(100, value));
}

function getProductiveTimeMs(categories: Record<string, number> = {}) {
  return (
    Number(categories.exam ?? 0) +
    Number(categories.quiz ?? 0) +
    Number(categories.education ?? 0) +
    Number(categories.learning ?? 0)
  );
}

function getExamFocusPercent(browsing: any) {
  if (!browsing) return 0;
  if (typeof browsing.examFocusPercent === 'number') {
    return clamp(Math.round(browsing.examFocusPercent));
  }
  if (typeof browsing.examTimePercent === 'number') {
    return clamp(Math.round(browsing.examTimePercent));
  }

  const totalTime = Number(browsing.totalTime ?? 0);
  const productiveTime = getProductiveTimeMs(browsing.timeByCategory ?? {});

  if (totalTime > 0) {
    return clamp(Math.round((productiveTime / totalTime) * 100));
  }

  const activeCategory = String(browsing.activeSite?.category || '').toLowerCase();
  if (['exam', 'quiz', 'education', 'learning'].includes(activeCategory)) {
    return 100;
  }

  return 0;
}

export function BrowsingHealthCard({ browsing }: BrowsingHealthCardProps) {
  if (!browsing) return null;

  const risk = clamp(Number(browsing.browsingRiskScore ?? 0));
  const effort = clamp(Number(browsing.effortScore ?? 100));
  const openTabs = Number(browsing.openTabsCount ?? 0);
  const sitesVisited = Number(browsing.totalSitesVisited ?? browsing.uniqueSitesVisited ?? 0);
  const flaggedSites = Number(browsing.flaggedSitesCount ?? 0);
  const flaggedOpenTabs = Number(browsing.flaggedOpenTabs ?? 0);
  const activeSite = browsing.activeSite || null;
  const totalTime = Number(browsing.totalTime ?? 0);
  const examFocus = getExamFocusPercent(browsing);

  const riskBar = risk >= 60 ? 'bg-gradient-to-r from-rose-500 to-rose-400' : risk >= 30 ? 'bg-gradient-to-r from-amber-500 to-amber-400' : 'bg-gradient-to-r from-emerald-500 to-emerald-400';
  const effortBar = effort >= 70 ? 'bg-gradient-to-r from-emerald-500 to-emerald-400' : effort >= 40 ? 'bg-gradient-to-r from-amber-500 to-amber-400' : 'bg-gradient-to-r from-rose-500 to-rose-400';

  return (
    <div className="rounded-3xl border border-slate-200 bg-white text-slate-900 shadow-xl overflow-hidden">
      <div className="px-6 py-5 border-b border-slate-100 bg-slate-50/70">
        <div className="flex items-center gap-2">
          <Globe className="w-4 h-4 text-indigo-600" />
          <h3 className="text-lg font-semibold">Session & Browsing Health</h3>
        </div>
      </div>

      <div className="px-6 py-5 space-y-4">
        <div>
          <div className="flex items-center justify-between text-xs font-semibold text-slate-500 mb-2">
            <span>Risk</span>
            <span>{risk}</span>
          </div>
          <div className="h-2 rounded-full bg-slate-100 overflow-hidden">
            <div className={`h-full rounded-full ${riskBar}`} style={{ width: `${risk}%` }} />
          </div>
        </div>

        <div>
          <div className="flex items-center justify-between text-xs font-semibold text-slate-500 mb-2">
            <span>Effort</span>
            <span>{effort}</span>
          </div>
          <div className="h-2 rounded-full bg-slate-100 overflow-hidden">
            <div className={`h-full rounded-full ${effortBar}`} style={{ width: `${effort}%` }} />
          </div>
        </div>

        <div className="border-t border-slate-100 pt-4 space-y-3">
          <div className="flex items-center justify-between text-sm text-slate-600">
            <span className="flex items-center gap-2">
              <span className="text-slate-400">📑</span>
              Open Tabs:
            </span>
            <strong>{openTabs}</strong>
          </div>

          <div className="flex items-center justify-between text-sm text-slate-600">
            <span className="flex items-center gap-2">
              <span className="text-slate-400">🔍</span>
              Sites Visited:
            </span>
            <strong>{sitesVisited}{flaggedSites > 0 ? ` (${flaggedSites} flagged)` : ''}</strong>
          </div>

          <div className="flex items-center justify-between text-sm text-slate-600">
            <span className="flex items-center gap-2">
              <Target className="w-4 h-4 text-slate-400" />
              Exam Focus:
            </span>
            <strong className={examFocus > 70 ? 'text-emerald-600' : examFocus > 40 ? 'text-amber-600' : 'text-rose-600'}>
              {examFocus > 0 || totalTime > 0 ? `${examFocus}%` : '-'}
            </strong>
          </div>

          <div className="flex items-center justify-between text-sm text-slate-600 border-t border-dashed border-slate-200 pt-3">
            <span className="flex items-center gap-2">
              <MapPin className="w-4 h-4 text-slate-400" />
              Current:
            </span>
            <strong className="truncate ml-3 text-right">
              {activeSite ? formatHost(activeSite.url) : 'none'}
            </strong>
          </div>
          {activeSite && (
            <div className="flex items-center justify-end gap-2">
              <span className="rounded-full bg-emerald-50 px-2.5 py-1 text-[10px] font-bold uppercase tracking-wider text-emerald-700 border border-emerald-100">
                {String(activeSite.category || 'other').toUpperCase()}
              </span>
              <span className="rounded-full bg-slate-100 px-2.5 py-1 text-[10px] font-bold uppercase tracking-wider text-slate-600 border border-slate-200">
                {String(activeSite.riskLevel || 'none').toUpperCase()}
              </span>
            </div>
          )}
          {flaggedOpenTabs > 0 && (
            <div className="flex items-center gap-2 text-xs text-rose-600">
              <Activity className="w-3.5 h-3.5" />
              {flaggedOpenTabs} flagged open tab{flaggedOpenTabs === 1 ? '' : 's'}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}