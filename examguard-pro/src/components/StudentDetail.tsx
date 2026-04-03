import { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { ArrowLeft, User, Shield, Clock, FileText, AlertTriangle, CheckCircle, Loader2 } from "lucide-react";
import { config } from "../config";

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
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchStudentSessions = async () => {
      setLoading(true);
      try {
        const token = localStorage.getItem("token");
        const res = await fetch(`${config.apiUrl}/sessions`, {
          headers: token ? { Authorization: `Bearer ${token}` } : {},
        });
        if (!res.ok) throw new Error("Failed to fetch sessions");
        const data = await res.json();
        // Filter sessions for this student
        const studentSessions = data.filter(
          (s: any) => s.student_id === studentId
        );
        setSessions(studentSessions);
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

  const totalSessions = sessions.length;
  const activeSessions = sessions.filter(s => s.status === "active").length;

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
          <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center text-white text-xl font-bold shadow-lg">
            <User className="w-7 h-7" />
          </div>
          <div className="flex-1">
            <h1 className="text-2xl font-bold text-slate-900 tracking-tight">
              Student: {studentId}
            </h1>
            <p className="text-slate-500 mt-1 text-sm">
              Exam monitoring profile and session history
            </p>
          </div>
        </div>

        {/* Stats row */}
        <div className="grid grid-cols-3 gap-4 mt-6">
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
        </div>
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
                <th className="px-6 py-4 font-semibold text-xs uppercase tracking-wider text-right">Actions</th>
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
                      View Details
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
