import { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { ArrowLeft, User, Shield, Clock, FileText, AlertTriangle, CheckCircle, Loader2, Sparkles, TrendingUp, BadgeCheck } from "lucide-react";
import { config } from "../config";
import { BrowsingHealthCard } from "./BrowsingHealthCard";

interface StudentSession {
  id: string;
  exam_id: string;
  started_at: string;
  ended_at?: string;
  risk_score: number;
  risk_level: string;
  status: string;
}

export function StudentDetail() {
  const { studentId } = useParams<{ studentId: string }>();
  const navigate = useNavigate();
  const [sessions, setSessions] = useState<StudentSession[]>([]);
  const [studentProfile, setStudentProfile] = useState<any>(null);
  const [latestSessionSummary, setLatestSessionSummary] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchStudentSessions = async () => {
      setLoading(true);
      setError(null);
      try {
        const [studentRes, sessionsRes] = await Promise.all([
          fetch(`${config.apiUrl}/students/${studentId}`),
          fetch(`${config.apiUrl}/sessions?active_only=false&limit=500`),
        ]);

        if (studentRes.ok) {
          setStudentProfile(await studentRes.json());
        }

        if (!sessionsRes.ok) {
          throw new Error("Failed to fetch sessions");
        }

        const data = await sessionsRes.json();
        const studentSessions = data
          .filter((session: any) => session.student_id === studentId)
          .sort((a: any, b: any) => new Date(b.started_at).getTime() - new Date(a.started_at).getTime());

        setSessions(studentSessions);

        if (studentSessions.length > 0) {
          const latestSession = studentSessions[0];
          try {
            const detailRes = await fetch(`${config.apiUrl}/sessions/${latestSession.id}`);
            if (detailRes.ok) {
              setLatestSessionSummary(await detailRes.json());
            }
          } catch {
            setLatestSessionSummary(null);
          }
        } else {
          setLatestSessionSummary(null);
        }
      } catch (e: any) {
        setError(e.message);
      } finally {
        setLoading(false);
      }
    };
    fetchStudentSessions();
  }, [studentId]);

  const getRiskColor = (level: string) => {
    switch (level) {
      case "safe": return "text-emerald-600 bg-emerald-50 border-emerald-200";
      case "review": return "text-amber-600 bg-amber-50 border-amber-200";
      case "suspicious": return "text-red-600 bg-red-50 border-red-200";
      default: return "text-slate-600 bg-slate-50 border-slate-200";
    }
  };

  const avgRisk = sessions.length > 0
    ? (sessions.reduce((sum, s) => sum + s.risk_score, 0) / sessions.length).toFixed(1)
    : "0";
  const avgEffort = sessions.length > 0
    ? (sessions.reduce((sum, s) => sum + Number((s as any).engagement_score || (s as any).effort_alignment || 0), 0) / sessions.length).toFixed(1)
    : "0";

  const totalSessions = sessions.length;
  const activeSessions = sessions.filter(s => s.status === "active").length;
  const flaggedSessions = sessions.filter(s => s.risk_level === "review" || s.risk_level === "suspicious").length;
  const mostRecentSession = sessions[0] || null;
  const reportSummary = sessions.length > 0
    ? `Based on ${totalSessions} attended session${totalSessions === 1 ? '' : 's'}, the average risk is ${avgRisk}/100 and the average effort is ${avgEffort}/100. The most recent session was ${mostRecentSession?.exam_id || 'unknown exam'}.`
    : 'No attended sessions were found for this student yet.';

  const displayName = studentProfile?.name || studentId;

  return (
    <div className="space-y-6 max-w-5xl mx-auto">
      {/* Back button */}
      <button
        onClick={() => navigate(-1)}
        className="inline-flex items-center gap-2 text-sm text-slate-500 hover:text-indigo-600 transition-colors"
      >
        <ArrowLeft className="w-4 h-4" />
        Back
      </button>

      {/* Student Header */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-6">
        <div className="flex items-center gap-5">
          <div className="w-16 h-16 rounded-2xl bg-indigo-50 flex items-center justify-center text-indigo-700 text-xl font-bold shadow-sm border border-indigo-100">
            <User className="w-7 h-7" />
          </div>
          <div className="flex-1">
            <h1 className="text-2xl font-bold text-slate-900 tracking-tight">
              {displayName}
            </h1>
            <p className="text-slate-500 mt-1 text-sm">
              {studentProfile?.department || 'Exam monitoring profile'}{studentProfile?.year ? ` • ${studentProfile.year}` : ''}
            </p>
            <p className="text-xs text-slate-400 mt-1">Student ID: {studentId}</p>
          </div>
        </div>

        {/* Stats row */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mt-6">
          <div className="bg-slate-50 rounded-xl p-4 border border-slate-100">
            <div className="flex items-center gap-2 text-slate-500 text-xs font-semibold uppercase tracking-wider">
              <FileText className="w-3.5 h-3.5" />
              Total Sessions
            </div>
            <p className="text-2xl font-bold text-slate-900 mt-1">{totalSessions}</p>
          </div>
          <div className="bg-slate-50 rounded-xl p-4 border border-slate-100">
            <div className="flex items-center gap-2 text-slate-500 text-xs font-semibold uppercase tracking-wider">
              <Clock className="w-3.5 h-3.5" />
              Active Now
            </div>
            <p className="text-2xl font-bold text-emerald-600 mt-1">{activeSessions}</p>
          </div>
          <div className="bg-slate-50 rounded-xl p-4 border border-slate-100">
            <div className="flex items-center gap-2 text-slate-500 text-xs font-semibold uppercase tracking-wider">
              <Shield className="w-3.5 h-3.5" />
              Avg Risk Score
            </div>
            <p className="text-2xl font-bold text-slate-900 mt-1">{avgRisk}</p>
          </div>
          <div className="bg-slate-50 rounded-xl p-4 border border-slate-100">
            <div className="flex items-center gap-2 text-slate-500 text-xs font-semibold uppercase tracking-wider">
              <BadgeCheck className="w-3.5 h-3.5" />
              Flagged Sessions
            </div>
            <p className="text-2xl font-bold text-rose-600 mt-1">{flaggedSessions}</p>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-[minmax(0,1fr)_360px] gap-4">
        <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-6">
          <div className="flex items-start justify-between gap-4 mb-4">
            <div>
              <h2 className="text-lg font-bold text-slate-900 flex items-center gap-2">
                <Sparkles className="w-5 h-5 text-indigo-500" />
                Student Report
              </h2>
              <p className="text-sm text-slate-500 mt-1">Attendance-based summary built from the sessions this student has joined.</p>
            </div>
            {mostRecentSession && (
              <span className={`inline-flex items-center px-3 py-1 rounded-full text-xs font-semibold border ${
                mostRecentSession.risk_level === 'suspicious' ? 'bg-rose-50 text-rose-700 border-rose-200' :
                mostRecentSession.risk_level === 'review' ? 'bg-amber-50 text-amber-700 border-amber-200' :
                'bg-emerald-50 text-emerald-700 border-emerald-200'
              }`}>
                <TrendingUp className="w-3.5 h-3.5 mr-1.5" />
                Latest: {mostRecentSession.exam_id}
              </span>
            )}
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="rounded-xl border border-slate-200 bg-slate-50 p-4">
              <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-400">Report Summary</p>
              <p className="mt-2 text-sm text-slate-700 leading-6">{reportSummary}</p>
            </div>

            <div className="rounded-xl border border-slate-200 bg-slate-50 p-4">
              <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-400">Latest Session</p>
              {mostRecentSession ? (
                <div className="mt-2 space-y-1 text-sm text-slate-700">
                  <p><strong className="text-slate-900">Exam:</strong> {mostRecentSession.exam_id}</p>
                  <p><strong className="text-slate-900">Started:</strong> {new Date(mostRecentSession.started_at).toLocaleString()}</p>
                  <p><strong className="text-slate-900">Status:</strong> {mostRecentSession.status}</p>
                  <p><strong className="text-slate-900">Risk:</strong> {mostRecentSession.risk_score.toFixed(1)} / {mostRecentSession.risk_level}</p>
                </div>
              ) : (
                <p className="mt-2 text-sm text-slate-500">No recent session available.</p>
              )}
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mt-4">
            <div className="rounded-xl border border-slate-200 bg-white p-4">
              <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-400">Attendance</p>
              <p className="mt-1 text-2xl font-bold text-slate-900">{totalSessions}</p>
            </div>
            <div className="rounded-xl border border-slate-200 bg-white p-4">
              <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-400">Average Effort</p>
              <p className="mt-1 text-2xl font-bold text-slate-900">{avgEffort}</p>
            </div>
            <div className="rounded-xl border border-slate-200 bg-white p-4">
              <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-400">Active Rate</p>
              <p className="mt-1 text-2xl font-bold text-slate-900">{totalSessions > 0 ? Math.round((activeSessions / totalSessions) * 100) : 0}%</p>
            </div>
          </div>
        </div>

        {latestSessionSummary?.browsing && (
          <BrowsingHealthCard browsing={latestSessionSummary.browsing} />
        )}
      </div>

      {/* Sessions Table */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
        <div className="p-5 border-b border-slate-200 bg-slate-50/50">
          <h2 className="font-semibold text-slate-900">Session History</h2>
        </div>

        {loading ? (
          <div className="flex items-center justify-center py-16">
            <Loader2 className="w-6 h-6 animate-spin text-indigo-600" />
            <span className="ml-3 text-slate-500">Loading sessions...</span>
          </div>
        ) : error ? (
          <div className="flex items-center justify-center py-16 text-red-500">
            <AlertTriangle className="w-5 h-5 mr-2" />
            {error}
          </div>
        ) : sessions.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-16 text-slate-400">
            <FileText className="w-10 h-10 mb-3 opacity-40" />
            <p className="text-sm">No sessions found for this student.</p>
          </div>
        ) : (
          <table className="w-full text-left text-sm">
            <thead className="bg-slate-50 text-slate-500 border-b border-slate-200">
              <tr>
                <th className="px-6 py-4 font-semibold text-xs uppercase tracking-wider">Exam ID</th>
                <th className="px-6 py-4 font-semibold text-xs uppercase tracking-wider">Date</th>
                <th className="px-6 py-4 font-semibold text-xs uppercase tracking-wider">Status</th>
                <th className="px-6 py-4 font-semibold text-xs uppercase tracking-wider">Risk</th>
                <th className="px-6 py-4 font-semibold text-xs uppercase tracking-wider text-right">Session Report</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {sessions.map((session) => (
                <tr key={session.id} className="hover:bg-slate-50/80 transition-colors">
                  <td className="px-6 py-4 font-medium text-slate-900">{session.exam_id}</td>
                  <td className="px-6 py-4 text-slate-500">
                    {new Date(session.started_at).toLocaleString()}
                  </td>
                  <td className="px-6 py-4">
                    <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-semibold border ${
                      session.status === "active"
                        ? "bg-emerald-50 text-emerald-700 border-emerald-200"
                        : "bg-slate-50 text-slate-600 border-slate-200"
                    }`}>
                      {session.status === "active" ? <CheckCircle className="w-3 h-3" /> : <Clock className="w-3 h-3" />}
                      {session.status}
                    </span>
                  </td>
                  <td className="px-6 py-4">
                    <span className={`inline-flex items-center px-2.5 py-1 rounded-lg text-xs font-semibold border ${getRiskColor(session.risk_level)}`}>
                      {session.risk_score.toFixed(1)} — {session.risk_level}
                    </span>
                  </td>
                  <td className="px-6 py-4 text-right">
                    <button
                      onClick={() => navigate(`/sessions/${session.id}`)}
                      className="inline-flex items-center rounded-lg border border-slate-200 px-3 py-1.5 text-sm font-medium text-slate-700 hover:bg-slate-50 hover:border-indigo-200 hover:text-indigo-600 transition-colors bg-white shadow-sm active:scale-95"
                    >
                      Open Session
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
