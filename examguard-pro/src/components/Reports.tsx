import { useState, useEffect } from "react";
import { Download, FileText, Search, Calendar, Loader2, AlertCircle } from "lucide-react";
import { config } from "../config";

interface SessionItem {
  id: string;
  student_name: string;
  exam_id: string;
  started_at: string;
  ended_at?: string;
  risk_score: number;
  risk_level: string;
  status: string;
}

export function Reports() {
  const [sessions, setSessions] = useState<SessionItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [generating, setGenerating] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState("");

  const fetchSessions = async () => {
    setLoading(true);
    setError(null);
    try {
      const token = localStorage.getItem("token");
      const res = await fetch(`${config.apiUrl}/sessions`, {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      });
      if (!res.ok) throw new Error("Failed to fetch sessions");
      const data = await res.json();
      setSessions(data);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSessions();
  }, []);

  const downloadPdf = async (sessionId: string) => {
    setGenerating(sessionId);
    try {
      const token = localStorage.getItem("token");
      const res = await fetch(`${config.apiUrl}/reports/session/${sessionId}/pdf`, {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      });
      if (!res.ok) throw new Error("Failed to generate PDF");
      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `report_${sessionId}.pdf`;
      a.click();
      window.URL.revokeObjectURL(url);
    } catch (e: any) {
      alert(`Report generation failed: ${e.message}`);
    } finally {
      setGenerating(null);
    }
  };

  const downloadJson = async (sessionId: string) => {
    try {
      const token = localStorage.getItem("token");
      const res = await fetch(`${config.apiUrl}/reports/session/${sessionId}/json`, {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      });
      if (!res.ok) throw new Error("Failed to generate JSON report");
      const data = await res.json();
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `report_${sessionId}.json`;
      a.click();
      window.URL.revokeObjectURL(url);
    } catch (e: any) {
      alert(`JSON report failed: ${e.message}`);
    }
  };

  const filteredSessions = sessions.filter(
    (s) =>
      s.student_name?.toLowerCase().includes(search.toLowerCase()) ||
      s.exam_id?.toLowerCase().includes(search.toLowerCase()) ||
      s.id?.toLowerCase().includes(search.toLowerCase())
  );

  const getRiskBadge = (level: string) => {
    const colors: Record<string, string> = {
      safe: "bg-emerald-50 text-emerald-700 border-emerald-200",
      review: "bg-amber-50 text-amber-700 border-amber-200",
      suspicious: "bg-red-50 text-red-700 border-red-200",
    };
    return colors[level] || "bg-slate-50 text-slate-700 border-slate-200";
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Reports</h1>
          <p className="text-slate-500 mt-1">Generate and download detailed session reports.</p>
        </div>
        <button
          onClick={fetchSessions}
          className="inline-flex items-center justify-center rounded-xl bg-indigo-600 px-5 py-2.5 text-sm font-semibold text-white hover:bg-indigo-700 transition-colors shadow-sm active:scale-95 w-full sm:w-auto"
        >
          <FileText className="w-4 h-4 mr-2" />
          Refresh Sessions
        </button>
      </div>

      <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
        <div className="p-5 border-b border-slate-200 flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-slate-50/50">
          <div className="relative w-full sm:max-w-md">
            <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
            <input
              type="text"
              placeholder="Search by student, exam ID, or session..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full pl-10 pr-4 py-2 rounded-xl border border-slate-200 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-all bg-white text-slate-900 placeholder:text-slate-400"
            />
          </div>
          <div className="text-sm text-slate-500">
            {filteredSessions.length} session{filteredSessions.length !== 1 ? "s" : ""} available
          </div>
        </div>

        {loading ? (
          <div className="flex items-center justify-center py-16">
            <Loader2 className="w-6 h-6 animate-spin text-indigo-600" />
            <span className="ml-3 text-slate-500">Loading sessions...</span>
          </div>
        ) : error ? (
          <div className="flex items-center justify-center py-16 text-red-500">
            <AlertCircle className="w-5 h-5 mr-2" />
            {error}
          </div>
        ) : filteredSessions.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-16 text-slate-400">
            <FileText className="w-10 h-10 mb-3 opacity-40" />
            <p className="text-sm">No sessions found. Start an exam to generate reports.</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="bg-slate-50 text-slate-500 border-b border-slate-200">
                <tr>
                  <th className="px-6 py-4 font-semibold text-xs uppercase tracking-wider">Student</th>
                  <th className="px-6 py-4 font-semibold text-xs uppercase tracking-wider">Exam ID</th>
                  <th className="px-6 py-4 font-semibold text-xs uppercase tracking-wider">Date</th>
                  <th className="px-6 py-4 font-semibold text-xs uppercase tracking-wider">Risk</th>
                  <th className="px-6 py-4 font-semibold text-xs uppercase tracking-wider">Status</th>
                  <th className="px-6 py-4 font-semibold text-xs uppercase tracking-wider text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {filteredSessions.map((session) => (
                  <tr key={session.id} className="hover:bg-slate-50/80 transition-colors group">
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-3.5">
                        <div className="p-2 rounded-lg bg-indigo-50 text-indigo-600 border border-indigo-100 shadow-sm">
                          <FileText className="w-4 h-4" />
                        </div>
                        <div>
                          <span className="font-medium text-slate-900">{session.student_name}</span>
                          <p className="text-xs text-slate-400 mt-0.5">{session.id.substring(0, 8)}...</p>
                        </div>
                      </div>
                    </td>
                    <td className="px-6 py-4 text-slate-600 font-medium">{session.exam_id}</td>
                    <td className="px-6 py-4 text-slate-500">
                      {new Date(session.started_at).toLocaleDateString()}
                    </td>
                    <td className="px-6 py-4">
                      <span className={`inline-flex items-center px-2.5 py-1 rounded-lg text-xs font-semibold border ${getRiskBadge(session.risk_level)}`}>
                        {session.risk_level}
                      </span>
                    </td>
                    <td className="px-6 py-4">
                      <span className={`inline-flex items-center px-2.5 py-1 rounded-lg text-xs font-semibold border ${
                        session.status === "active"
                          ? "bg-emerald-50 text-emerald-700 border-emerald-200"
                          : "bg-slate-50 text-slate-600 border-slate-200"
                      }`}>
                        {session.status}
                      </span>
                    </td>
                    <td className="px-6 py-4 text-right">
                      <div className="flex items-center justify-end gap-2">
                        <button
                          onClick={() => downloadPdf(session.id)}
                          disabled={generating === session.id}
                          className="inline-flex items-center justify-center rounded-lg border border-slate-200 px-3 py-1.5 text-sm font-medium text-slate-700 hover:bg-slate-50 hover:border-indigo-200 hover:text-indigo-600 transition-colors bg-white shadow-sm active:scale-95 disabled:opacity-50"
                        >
                          {generating === session.id ? (
                            <Loader2 className="w-4 h-4 mr-1 animate-spin" />
                          ) : (
                            <Download className="w-4 h-4 mr-1" />
                          )}
                          PDF
                        </button>
                        <button
                          onClick={() => downloadJson(session.id)}
                          className="inline-flex items-center justify-center rounded-lg border border-slate-200 px-3 py-1.5 text-sm font-medium text-slate-700 hover:bg-slate-50 hover:border-indigo-200 hover:text-indigo-600 transition-colors bg-white shadow-sm active:scale-95"
                        >
                          <Download className="w-4 h-4 mr-1" />
                          JSON
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
