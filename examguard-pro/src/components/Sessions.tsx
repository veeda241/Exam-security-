import { Search, Video, Users, ChevronRight, Clock, ShieldAlert, Trash2 } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { motion } from "motion/react";
import React, { useState, useMemo, useEffect } from "react";
import { config } from '../config';

interface SessionData {
  id: string;
  student_name: string;
  student_id: string;
  exam_id: string;
  status: string;
  risk_level: string;
  risk_score: number;
  engagement_score: number;
  started_at: string;
}

interface ExamGroup {
  exam_id: string;
  proctor_session_id: string;
  status: string;
  started_at: string;
  students: SessionData[];
  avg_risk: number;
  flagged_count: number;
}

export function Sessions() {
  const navigate = useNavigate();
  const [sessions, setSessions] = useState<SessionData[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');

  useEffect(() => {
    const fetchSessions = async () => {
      try {
        const response = await fetch(`${config.apiUrl}/sessions`);
        if (response.ok) {
          const data = await response.json();
          setSessions(data);
        }
      } catch (error) {
        console.error("Failed to fetch sessions:", error);
      } finally {
        setIsLoading(false);
      }
    };
    fetchSessions();
  }, []);

  // Group sessions by exam_id. The proctor session has student_id starting with "PROCTOR-"
  const examGroups: ExamGroup[] = useMemo(() => {
    const groups: Record<string, ExamGroup> = {};

    for (const s of sessions) {
      const examId = s.exam_id;
      if (!groups[examId]) {
        groups[examId] = {
          exam_id: examId,
          proctor_session_id: '',
          status: 'active',
          started_at: s.started_at,
          students: [],
          avg_risk: 0,
          flagged_count: 0,
        };
      }

      if (s.student_id?.startsWith('PROCTOR-')) {
        groups[examId].proctor_session_id = s.id;
        groups[examId].status = s.status;
        groups[examId].started_at = s.started_at;
      } else {
        groups[examId].students.push(s);
      }
    }

    // Calculate stats for each group
    return Object.values(groups)
      .map(g => {
        if (g.students.length > 0) {
          g.avg_risk = Math.round(g.students.reduce((a, s) => a + (s.risk_score || 0), 0) / g.students.length);
          g.flagged_count = g.students.filter(s => s.risk_level === 'review' || s.risk_level === 'suspicious').length;
        }
        return g;
      })
      // Filter out orphan groups: must have a proctor session OR at least 1 student
      // Also filter out groups with non-EXAM exam_ids that have 0 students (these are solo orphan sessions)
      .filter(g => {
        // Always show groups that have students
        if (g.students.length > 0) return true;
        // Show empty groups only if they have a proctor session (waiting for students to join)
        if (g.proctor_session_id) return true;
        // Hide orphan empty groups
        return false;
      })
      .filter(g => {
        if (!searchQuery) return true;
        const q = searchQuery.toLowerCase();
        return g.exam_id.toLowerCase().includes(q) ||
          g.students.some(s => s.student_name?.toLowerCase().includes(q) || s.student_id?.toLowerCase().includes(q));
      })
      .sort((a, b) => new Date(b.started_at).getTime() - new Date(a.started_at).getTime());
  }, [sessions, searchQuery]);

  const formatTime = (iso: string) => {
    try {
      const d = new Date(iso);
      return d.toLocaleString('en-US', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
    } catch { return iso; }
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Exam Sessions</h1>
          <p className="text-slate-500 mt-1">Manage and monitor active exam sessions.</p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={async () => {
              if (confirm("Are you sure you want to clear ALL session data? This cannot be undone.")) {
                try {
                  const res = await fetch(`${config.apiUrl}/sessions/clear`, { method: 'DELETE' });
                  if (res.ok) {
                    setSessions([]);
                  }
                } catch (e) {
                  alert("Failed to clear sessions");
                }
              }
            }}
            className="inline-flex items-center justify-center rounded-xl bg-white border border-rose-200 px-4 py-2.5 text-sm font-semibold text-rose-600 hover:bg-rose-50 transition-colors shadow-sm active:scale-95"
          >
            <Trash2 className="w-4 h-4 mr-2" />
            Clear All Sessions
          </button>
        </div>
      </div>

      {/* Search */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
        <div className="p-5 border-b border-slate-200 bg-slate-50/50">
          <div className="relative w-full sm:max-w-md">
            <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
            <input
              type="text"
              placeholder="Search by exam code or student..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-10 pr-4 py-2 rounded-xl border border-slate-200 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-all bg-white text-slate-900 placeholder:text-slate-400"
            />
          </div>
        </div>

        {isLoading ? (
          <div className="p-12 text-center text-slate-500">Loading sessions...</div>
        ) : examGroups.length === 0 ? (
          <div className="p-12 text-center text-slate-500">No exam sessions found.</div>
        ) : (
          <div className="divide-y divide-slate-100">
            {examGroups.map((group, idx) => {
              const isActive = group.status === 'active';
              return (
                <motion.div
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: idx * 0.05 }}
                  key={group.exam_id}
                  onClick={() => {
                    // Navigate to the proctor session detail, or first student session
                    const targetId = group.proctor_session_id || group.students[0]?.id;
                    if (targetId) navigate(`/sessions/${targetId}`);
                  }}
                  className="p-5 hover:bg-slate-50/80 transition-colors cursor-pointer group"
                >
                  <div className="flex items-center justify-between">
                    {/* Left side: Exam info */}
                    <div className="flex items-center gap-4">
                      <div className={`p-3 rounded-xl border shadow-sm ${
                        isActive
                          ? 'bg-emerald-50 border-emerald-100 text-emerald-600'
                          : 'bg-slate-100 border-slate-200 text-slate-500'
                      }`}>
                        <Video className="w-5 h-5" />
                      </div>
                      <div>
                        <div className="flex items-center gap-2.5">
                          <h3 className="text-lg font-bold text-slate-900 tracking-tight">
                            {group.exam_id}
                          </h3>
                          <span className={`inline-flex items-center px-2 py-0.5 rounded-md text-[10px] font-bold uppercase tracking-wider border ${
                            isActive
                              ? 'bg-emerald-50 text-emerald-700 border-emerald-200 animate-pulse'
                              : 'bg-slate-100 text-slate-600 border-slate-200'
                          }`}>
                            {isActive ? '● Live' : 'Ended'}
                          </span>
                        </div>
                        <div className="flex items-center gap-4 mt-1 text-xs text-slate-500">
                          <span className="flex items-center gap-1">
                            <Users className="w-3.5 h-3.5" />
                            {group.students.length} student{group.students.length !== 1 ? 's' : ''}
                          </span>
                          <span className="flex items-center gap-1">
                            <Clock className="w-3.5 h-3.5" />
                            {formatTime(group.started_at)}
                          </span>
                        </div>
                      </div>
                    </div>

                    {/* Right side: Stats + Arrow */}
                    <div className="flex items-center gap-5">
                      {/* Risk indicator */}
                      {group.students.length > 0 && (
                        <div className="hidden sm:flex items-center gap-4">
                          <div className="text-right">
                            <p className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider">Avg Risk</p>
                            <p className={`text-lg font-bold ${
                              group.avg_risk > 70 ? 'text-rose-600' :
                              group.avg_risk > 30 ? 'text-amber-500' :
                              'text-emerald-600'
                            }`}>
                              {group.avg_risk}
                            </p>
                          </div>
                          {group.flagged_count > 0 && (
                            <div className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg bg-rose-50 border border-rose-100">
                              <ShieldAlert className="w-3.5 h-3.5 text-rose-500" />
                              <span className="text-xs font-bold text-rose-600">{group.flagged_count} flagged</span>
                            </div>
                          )}
                        </div>
                      )}

                      {/* Student avatars preview */}
                      {group.students.length > 0 && (
                        <div className="hidden md:flex -space-x-2">
                          {group.students.slice(0, 4).map((s) => (
                            <div
                              key={s.id}
                              className="w-8 h-8 rounded-full bg-indigo-100 text-indigo-700 flex items-center justify-center text-[10px] font-bold border-2 border-white shadow-sm"
                              title={s.student_name || s.student_id}
                            >
                              {(s.student_name || s.student_id || '?').split(' ').map(n => n[0]).join('').toUpperCase().slice(0, 2)}
                            </div>
                          ))}
                          {group.students.length > 4 && (
                            <div className="w-8 h-8 rounded-full bg-slate-200 text-slate-600 flex items-center justify-center text-[10px] font-bold border-2 border-white shadow-sm">
                              +{group.students.length - 4}
                            </div>
                          )}
                        </div>
                      )}

                      <ChevronRight className="w-5 h-5 text-slate-300 group-hover:text-indigo-500 transition-colors" />
                    </div>
                  </div>
                </motion.div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
