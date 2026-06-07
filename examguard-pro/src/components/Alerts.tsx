import { useEffect, useMemo, useState, type MouseEvent } from "react";
import { useNavigate } from "react-router-dom";
import { AlertTriangle, Search, Filter, Eye, Check, X, ShieldAlert, Clock, Video, TrendingUp, ChevronRight } from "lucide-react";
import { motion, AnimatePresence } from "motion/react";
import { config } from "../config";

type AlertStatus = "unresolved" | "resolved";
type AlertSeverity = "high" | "medium" | "low";

interface StudentProfile {
  id: string;
  name: string;
  email?: string | null;
  department?: string | null;
  year?: string | null;
}

interface StudentAlert {
  studentId: string;
  studentName: string;
  studentProfile: StudentProfile | null;
  sessionId: string;
  startedAt: string;
  endedAt: string;
  riskScore: number;
  effortScore: number;
  riskGap: number;
  riskLevel: string;
}

interface SessionAlertGroup {
  id: string;
  examId: string;
  proctorSessionId: string | null;
  startedAt: string;
  endedAt: string;
  participantsCount: number;
  flaggedStudents: StudentAlert[];
  avgRisk: number;
  avgEffort: number;
  avgGap: number;
  severity: AlertSeverity;
  status: AlertStatus;
}

function formatDateTime(value: string) {
  try {
    return new Date(value).toLocaleString();
  } catch {
    return value;
  }
}

function getSeverity(riskGap: number, riskScore: number): AlertSeverity {
  if (riskGap >= 25 || riskScore >= 80) return "high";
  if (riskGap >= 10 || riskScore >= 55) return "medium";
  return "low";
}

function getInitials(name: string) {
  const initials = name
    .split(" ")
    .map((part) => part[0])
    .join("")
    .slice(0, 2)
    .toUpperCase();

  return initials || "?";
}

export function Alerts() {
  const navigate = useNavigate();
  const [alerts, setAlerts] = useState<SessionAlertGroup[]>([]);
  const [searchQuery, setSearchQuery] = useState("");
  const [filterStatus, setFilterStatus] = useState<"All" | "Unresolved" | "Resolved">("All");
  const [selectedAlert, setSelectedAlert] = useState<SessionAlertGroup | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const fetchAlerts = async () => {
      setIsLoading(true);
      try {
        const [sessionsRes, studentsRes] = await Promise.all([
          fetch(`${config.apiUrl}/sessions?active_only=false&limit=500`),
          fetch(`${config.apiUrl}/students?limit=500`),
        ]);

        if (!sessionsRes.ok) {
          throw new Error(`Failed to fetch sessions (${sessionsRes.status})`);
        }

        const sessions = await sessionsRes.json();
        const students = studentsRes.ok ? await studentsRes.json() : [];
        const studentMap = new Map<string, StudentProfile>();

        for (const student of students) {
          studentMap.set(student.id, student);
        }

        const sessionGroups = new Map<string, {
          examId: string;
          proctorSessionId: string | null;
          startedAt: string;
          endedAt: string;
          participantIds: Set<string>;
          flaggedStudents: StudentAlert[];
        }>();

        for (const session of sessions) {
          const examId = String(session.exam_id || "Unknown");
          const startedAt = session.started_at || new Date().toISOString();
          const endedAt = session.ended_at || startedAt;
          const sessionGroupKey = String(session.proctor_session_id || examId);

          if (!sessionGroups.has(sessionGroupKey)) {
            sessionGroups.set(sessionGroupKey, {
              examId,
              proctorSessionId: null,
              startedAt,
              endedAt,
              participantIds: new Set<string>(),
              flaggedStudents: [],
            });
          }

          const group = sessionGroups.get(sessionGroupKey)!;

          if (new Date(startedAt).getTime() < new Date(group.startedAt).getTime()) {
            group.startedAt = startedAt;
          }
          if (new Date(endedAt).getTime() > new Date(group.endedAt).getTime()) {
            group.endedAt = endedAt;
          }

          const studentId = String(session.student_id || "");
          if (studentId.startsWith("PROCTOR-")) {
            group.proctorSessionId = session.id;
            continue;
          }

          if (session.proctor_session_id) {
            group.proctorSessionId = session.proctor_session_id;
          }

          group.participantIds.add(studentId || session.id);

          const riskScore = Number(session.risk_score ?? 0);
          const effortScore = Number(session.effort_alignment ?? session.engagement_score ?? 0);
          const sessionEnded = String(session.status || "").toLowerCase() === "ended" && Boolean(session.ended_at);
          const isAlert = sessionEnded && riskScore > effortScore;

          if (!isAlert) {
            continue;
          }

          group.flaggedStudents.push({
            studentId: studentId || session.id,
            studentName: session.student_name || studentMap.get(studentId)?.name || studentId || "Unknown",
            studentProfile: studentMap.get(studentId) || null,
            sessionId: session.id,
            startedAt,
            endedAt,
            riskScore,
            effortScore,
            riskGap: Math.round((riskScore - effortScore) * 10) / 10,
            riskLevel: session.risk_level || "review",
          });
        }

        const derivedAlerts: SessionAlertGroup[] = Array.from(sessionGroups.values())
          .filter((group) => group.flaggedStudents.length > 0)
          .map((group) => {
            const flaggedStudents = [...group.flaggedStudents].sort((a, b) => {
              if (b.riskGap !== a.riskGap) return b.riskGap - a.riskGap;
              return b.riskScore - a.riskScore;
            });

            const avgRisk = Math.round(flaggedStudents.reduce((sum, student) => sum + student.riskScore, 0) / flaggedStudents.length);
            const avgEffort = Math.round(flaggedStudents.reduce((sum, student) => sum + student.effortScore, 0) / flaggedStudents.length);
            const avgGap = Math.round(flaggedStudents.reduce((sum, student) => sum + student.riskGap, 0) / flaggedStudents.length);
            const topStudent = flaggedStudents[0];

            return {
              id: group.proctorSessionId || group.examId,
              examId: group.examId,
              proctorSessionId: group.proctorSessionId,
              startedAt: group.startedAt,
              endedAt: group.endedAt,
              participantsCount: group.participantIds.size,
              flaggedStudents,
              avgRisk,
              avgEffort,
              avgGap,
              severity: getSeverity(topStudent.riskGap, topStudent.riskScore),
              status: "unresolved" as AlertStatus,
            };
          })
          .sort((a, b) => new Date(b.endedAt).getTime() - new Date(a.endedAt).getTime());

        setAlerts(derivedAlerts);
      } catch (error) {
        console.error("Failed to load alerts:", error);
        setAlerts([]);
      } finally {
        setIsLoading(false);
      }
    };

    fetchAlerts();
  }, []);

  const handleResolve = (id: string, e?: MouseEvent<HTMLButtonElement>) => {
    if (e) e.stopPropagation();
    setAlerts((currentAlerts) => currentAlerts.map((alert) => (alert.id === id ? { ...alert, status: "resolved" } : alert)));
  };

  const filteredAlerts = useMemo(() => {
    const query = searchQuery.toLowerCase().trim();

    return alerts.filter((alert) => {
      const matchesSearch =
        alert.examId.toLowerCase().includes(query) ||
        alert.flaggedStudents.some((student) =>
          student.studentName.toLowerCase().includes(query) ||
          student.studentId.toLowerCase().includes(query) ||
          student.sessionId.toLowerCase().includes(query)
        );

      const matchesStatus =
        filterStatus === "All" ||
        (filterStatus === "Unresolved" && alert.status === "unresolved") ||
        (filterStatus === "Resolved" && alert.status === "resolved");

      return matchesSearch && matchesStatus;
    });
  }, [alerts, searchQuery, filterStatus]);

  const unresolvedCount = alerts.filter((alert) => alert.status === "unresolved").length;
  const highSeverityCount = alerts.filter((alert) => alert.status === "unresolved" && alert.severity === "high").length;
  const totalFlaggedStudents = alerts.reduce((sum, alert) => sum + alert.flaggedStudents.length, 0);
  const avgGap = alerts.length > 0
    ? Math.round((alerts.reduce((sum, alert) => sum + alert.avgGap, 0) / alerts.length) * 10) / 10
    : 0;

  const openExamSession = (alert: SessionAlertGroup) => {
    if (!alert.proctorSessionId) {
      return;
    }

    navigate(`/sessions/${alert.proctorSessionId}`);
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-20 md:pb-0">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Exam Session Alerts</h1>
          <p className="text-slate-500 mt-1 text-sm">
            Each alert represents an exam session. The students listed inside it are the ones who joined under that session and finished with risk higher than effort.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <div className="bg-white px-4 py-2 rounded-xl border border-slate-200 shadow-sm flex items-center gap-3">
            <div className="flex items-center gap-2">
              <div className="w-2 h-2 rounded-full bg-rose-500 animate-pulse" />
              <span className="text-sm font-medium text-slate-700">{highSeverityCount} Critical</span>
            </div>
            <div className="w-px h-4 bg-slate-200" />
            <div className="flex items-center gap-2">
              <div className="w-2 h-2 rounded-full bg-amber-500" />
              <span className="text-sm font-medium text-slate-700">{unresolvedCount} Unresolved</span>
            </div>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-400">Alert Sessions</p>
          <p className="mt-1 text-3xl font-bold text-slate-900">{alerts.length}</p>
        </div>
        <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-400">Flagged Students</p>
          <p className="mt-1 text-3xl font-bold text-emerald-600">{totalFlaggedStudents}</p>
        </div>
        <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-400">Critical</p>
          <p className="mt-1 text-3xl font-bold text-rose-600">{highSeverityCount}</p>
        </div>
        <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-400">Avg Risk Gap</p>
          <p className="mt-1 text-3xl font-bold text-slate-900">{avgGap}</p>
        </div>
      </div>

      <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
        <div className="p-5 border-b border-slate-200 flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-slate-50/50">
          <div className="relative w-full sm:max-w-md">
            <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
            <input
              type="text"
              placeholder="Search by exam, student, or session..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-10 pr-4 py-2 rounded-xl border border-slate-200 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-all bg-white text-slate-900 placeholder:text-slate-400"
            />
          </div>
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-slate-400">
              <Filter className="w-4 h-4" />
              Filter
            </div>
            <select
              value={filterStatus}
              onChange={(e) => setFilterStatus(e.target.value as typeof filterStatus)}
              className="px-3.5 py-2 rounded-xl border border-slate-200 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 bg-white cursor-pointer text-slate-700 font-medium"
            >
              <option value="All">All Status</option>
              <option value="Unresolved">Unresolved</option>
              <option value="Resolved">Resolved</option>
            </select>
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="bg-slate-50 text-slate-500 border-b border-slate-200">
              <tr>
                <th className="px-6 py-4 font-semibold text-xs uppercase tracking-wider">Exam Session</th>
                <th className="px-6 py-4 font-semibold text-xs uppercase tracking-wider">Flagged Students</th>
                <th className="px-6 py-4 font-semibold text-xs uppercase tracking-wider">Risk vs Effort</th>
                <th className="px-6 py-4 font-semibold text-xs uppercase tracking-wider">Ended</th>
                <th className="px-6 py-4 font-semibold text-xs uppercase tracking-wider">Status</th>
                <th className="px-6 py-4 font-semibold text-xs uppercase tracking-wider text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              <AnimatePresence>
                {isLoading ? (
                  <tr>
                    <td colSpan={6} className="px-6 py-16 text-center text-slate-500">Loading alerts...</td>
                  </tr>
                ) : filteredAlerts.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="px-6 py-12 text-center text-slate-500">
                      <ShieldAlert className="w-12 h-12 mx-auto text-slate-300 mb-3" />
                      <p className="text-lg font-medium text-slate-900">No risk alerts found</p>
                      <p className="text-sm">Only exam sessions with students whose risk ended higher than effort appear here.</p>
                    </td>
                  </tr>
                ) : (
                  filteredAlerts.map((alert, idx) => (
                    <motion.tr
                      initial={{ opacity: 0, y: 10 }}
                      animate={{ opacity: 1, y: 0 }}
                      exit={{ opacity: 0, scale: 0.95 }}
                      transition={{ delay: idx * 0.05 }}
                      key={alert.id}
                      onClick={() => setSelectedAlert(alert)}
                      className="hover:bg-slate-50/80 transition-colors group cursor-pointer"
                    >
                      <td className="px-6 py-4">
                        <div className="flex items-center gap-3.5">
                          <div className={`p-2 rounded-lg border shadow-sm ${
                            alert.severity === "high"
                              ? "bg-rose-50 text-rose-600 border-rose-100"
                              : alert.severity === "medium"
                                ? "bg-amber-50 text-amber-600 border-amber-100"
                                : "bg-blue-50 text-blue-600 border-blue-100"
                          }`}>
                            <Video className="w-4 h-4" />
                          </div>
                          <div>
                            <p className="font-medium text-slate-900">{alert.examId}</p>
                            <p className="text-xs text-slate-500 mt-0.5">
                              {alert.participantsCount} participant{alert.participantsCount !== 1 ? "s" : ""}
                            </p>
                          </div>
                        </div>
                      </td>
                      <td className="px-6 py-4 text-slate-600">
                        <div className="flex flex-wrap items-center gap-2">
                          {alert.flaggedStudents.slice(0, 2).map((student) => (
                            <span
                              key={student.sessionId}
                              className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-indigo-50 text-indigo-700 border border-indigo-100 text-xs font-semibold"
                              title={student.studentId}
                            >
                              {getInitials(student.studentName)}
                              {student.studentName}
                            </span>
                          ))}
                          {alert.flaggedStudents.length > 2 && (
                            <span className="text-xs font-semibold text-slate-500">+{alert.flaggedStudents.length - 2} more</span>
                          )}
                        </div>
                      </td>
                      <td className="px-6 py-4">
                        <div className="space-y-1">
                          <div className="flex items-center gap-2 text-sm text-slate-700 font-medium">
                            <span className="text-rose-600">{alert.avgRisk}</span>
                            <span className="text-slate-300">/</span>
                            <span className="text-emerald-600">{alert.avgEffort}</span>
                          </div>
                          <div className="w-28 h-1.5 bg-slate-100 rounded-full overflow-hidden">
                            <div className="h-full bg-rose-500 rounded-full" style={{ width: `${Math.min(100, Math.max(0, alert.avgRisk))}%` }} />
                          </div>
                          <p className="text-[11px] text-slate-500">Gap: {alert.avgGap > 0 ? "+" : ""}{alert.avgGap}</p>
                        </div>
                      </td>
                      <td className="px-6 py-4 text-slate-500 text-[13px]">
                        <div className="flex items-center gap-1.5">
                          <Clock className="w-3.5 h-3.5" />
                          {formatDateTime(alert.endedAt)}
                        </div>
                      </td>
                      <td className="px-6 py-4">
                        <span className={`inline-flex items-center px-2.5 py-1 rounded-md text-xs font-semibold border ${
                          alert.status === "resolved"
                            ? "bg-emerald-50 text-emerald-700 border-emerald-200"
                            : "bg-rose-50 text-rose-700 border-rose-200"
                        }`}>
                          {alert.status.charAt(0).toUpperCase() + alert.status.slice(1)}
                        </span>
                      </td>
                      <td className="px-6 py-4 text-right">
                        <div className="flex items-center justify-end gap-2">
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              setSelectedAlert(alert);
                            }}
                            className="p-1.5 text-slate-400 hover:text-indigo-600 hover:bg-indigo-50 rounded-lg transition-colors opacity-0 group-hover:opacity-100 focus:opacity-100"
                            title="View session details"
                          >
                            <Eye className="w-4 h-4" />
                          </button>
                          {alert.proctorSessionId && (
                            <button
                              onClick={(e) => {
                                e.stopPropagation();
                                openExamSession(alert);
                              }}
                              className="p-1.5 text-slate-400 hover:text-indigo-600 hover:bg-indigo-50 rounded-lg transition-colors opacity-0 group-hover:opacity-100 focus:opacity-100"
                              title="Open Exam Session"
                            >
                              <ChevronRight className="w-4 h-4" />
                            </button>
                          )}
                          {alert.status === "unresolved" && (
                            <button
                              onClick={(e) => handleResolve(alert.id, e)}
                              className="p-1.5 text-slate-400 hover:text-emerald-600 hover:bg-emerald-50 rounded-lg transition-colors opacity-0 group-hover:opacity-100 focus:opacity-100"
                              title="Mark as Resolved"
                            >
                              <Check className="w-4 h-4" />
                            </button>
                          )}
                        </div>
                      </td>
                    </motion.tr>
                  ))
                )}
              </AnimatePresence>
            </tbody>
          </table>
        </div>
      </div>

      <AnimatePresence>
        {selectedAlert && (
          <div className="fixed inset-0 bg-slate-900/50 backdrop-blur-sm flex items-center justify-center z-50 p-4">
            <motion.div
              initial={{ opacity: 0, scale: 0.95, y: 10 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.95, y: 10 }}
              className="bg-white p-0 rounded-2xl w-[1100px] max-w-full shadow-xl flex flex-col overflow-hidden max-h-[90vh]"
            >
              <div className="flex items-center justify-between p-6 border-b border-slate-100 bg-slate-50/50 shrink-0">
                <div className="flex items-center gap-4">
                  <div className={`p-3 rounded-xl border shadow-sm ${
                    selectedAlert.severity === "high"
                      ? "bg-rose-50 text-rose-600 border-rose-100"
                      : selectedAlert.severity === "medium"
                        ? "bg-amber-50 text-amber-600 border-amber-100"
                        : "bg-blue-50 text-blue-600 border-blue-100"
                  }`}>
                    <AlertTriangle className="w-6 h-6" />
                  </div>
                  <div>
                    <h2 className="text-xl font-bold text-slate-900 tracking-tight">{selectedAlert.examId}</h2>
                    <p className="text-sm text-slate-500">
                      {selectedAlert.participantsCount} participant{selectedAlert.participantsCount !== 1 ? "s" : ""} total, {selectedAlert.flaggedStudents.length} flagged students
                    </p>
                  </div>
                </div>
                <button onClick={() => setSelectedAlert(null)} className="p-2 text-slate-400 hover:text-slate-600 hover:bg-slate-100 rounded-xl transition-colors">
                  <X className="w-5 h-5" />
                </button>
              </div>

              <div className="p-6 overflow-y-auto space-y-6">
                <div className="grid grid-cols-1 lg:grid-cols-[minmax(0,1fr)_340px] gap-4">
                  <div className="rounded-2xl border border-slate-200 bg-slate-50 p-5">
                    <div className="flex items-start justify-between gap-4">
                      <div>
                        <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-400">Alert Reason</p>
                        <h3 className="mt-2 text-lg font-bold text-slate-900">Exam session ended with higher risk than effort</h3>
                        <p className="mt-2 text-sm text-slate-600 leading-6">
                          This is an exam-session alert. The students below joined this session and ended the exam with a risk score above their effort score.
                        </p>
                      </div>
                      <span className={`inline-flex items-center px-3 py-1 rounded-full text-xs font-semibold border ${
                        selectedAlert.severity === "high"
                          ? "bg-rose-50 text-rose-700 border-rose-200"
                          : selectedAlert.severity === "medium"
                            ? "bg-amber-50 text-amber-700 border-amber-200"
                            : "bg-blue-50 text-blue-700 border-blue-200"
                      }`}>
                        <TrendingUp className="w-3.5 h-3.5 mr-1.5" />
                        {selectedAlert.severity.toUpperCase()}
                      </span>
                    </div>

                    <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 mt-4">
                      <div className="rounded-xl border border-slate-200 bg-white p-4">
                        <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-400">Avg Risk</p>
                        <p className="mt-1 text-2xl font-bold text-rose-600">{selectedAlert.avgRisk}</p>
                      </div>
                      <div className="rounded-xl border border-slate-200 bg-white p-4">
                        <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-400">Avg Effort</p>
                        <p className="mt-1 text-2xl font-bold text-emerald-600">{selectedAlert.avgEffort}</p>
                      </div>
                      <div className="rounded-xl border border-slate-200 bg-white p-4">
                        <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-400">Avg Gap</p>
                        <p className="mt-1 text-2xl font-bold text-slate-900">{selectedAlert.avgGap > 0 ? "+" : ""}{selectedAlert.avgGap}</p>
                      </div>
                    </div>

                    <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 mt-4">
                      <div className="rounded-xl border border-slate-200 bg-white p-4">
                        <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-400">Started</p>
                        <p className="mt-1 text-sm font-semibold text-slate-900">{formatDateTime(selectedAlert.startedAt)}</p>
                      </div>
                      <div className="rounded-xl border border-slate-200 bg-white p-4">
                        <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-400">Ended</p>
                        <p className="mt-1 text-sm font-semibold text-slate-900">{formatDateTime(selectedAlert.endedAt)}</p>
                      </div>
                      <div className="rounded-xl border border-slate-200 bg-white p-4">
                        <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-400">Participants</p>
                        <p className="mt-1 text-sm font-semibold text-slate-900">{selectedAlert.participantsCount}</p>
                      </div>
                    </div>
                  </div>

                  <div className="rounded-2xl border border-slate-200 bg-white p-5">
                    <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-400">Session Actions</p>
                    <div className="mt-3 space-y-3 text-sm text-slate-600">
                      <p>
                        Use the buttons below to open the exam session overview or jump to a student report.
                      </p>
                      <div className="rounded-xl border border-slate-200 bg-slate-50 p-4">
                        <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-400">Session Note</p>
                        <p className="mt-1 text-sm text-slate-700">
                          This alert is tied to the exam container. The student rows underneath are the joined students, not the session itself.
                        </p>
                      </div>
                    </div>
                  </div>
                </div>

                <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
                  <div className="p-5 border-b border-slate-200 bg-slate-50/50">
                    <h3 className="font-semibold text-slate-900">Students inside this session</h3>
                  </div>

                  <div className="overflow-x-auto">
                    <table className="w-full text-left text-sm">
                      <thead className="bg-white text-slate-500 border-b border-slate-200">
                        <tr>
                          <th className="px-6 py-4 font-semibold text-xs uppercase tracking-wider">Student</th>
                          <th className="px-6 py-4 font-semibold text-xs uppercase tracking-wider">Student Session</th>
                          <th className="px-6 py-4 font-semibold text-xs uppercase tracking-wider">Risk vs Effort</th>
                          <th className="px-6 py-4 font-semibold text-xs uppercase tracking-wider">End Time</th>
                          <th className="px-6 py-4 font-semibold text-xs uppercase tracking-wider text-right">Actions</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-100">
                        {selectedAlert.flaggedStudents.map((student) => (
                          <tr key={student.sessionId} className="hover:bg-slate-50/80 transition-colors">
                            <td className="px-6 py-4">
                              <div className="flex items-center gap-3.5">
                                <div className="w-10 h-10 rounded-full bg-indigo-100 text-indigo-700 flex items-center justify-center font-bold text-sm border border-indigo-200 shadow-sm">
                                  {getInitials(student.studentName)}
                                </div>
                                <div>
                                  <p className="font-medium text-slate-900">{student.studentName}</p>
                                  <p className="text-xs text-slate-500 mt-0.5">{student.studentId}</p>
                                  {student.studentProfile?.department && (
                                    <p className="text-[11px] text-slate-400 mt-0.5">
                                      {student.studentProfile.department}{student.studentProfile.year ? ` • ${student.studentProfile.year}` : ""}
                                    </p>
                                  )}
                                </div>
                              </div>
                            </td>
                            <td className="px-6 py-4 text-slate-600 font-medium">{student.sessionId}</td>
                            <td className="px-6 py-4">
                              <div className="space-y-1">
                                <div className="flex items-center gap-2 text-sm text-slate-700 font-medium">
                                  <span className="text-rose-600">{student.riskScore.toFixed(1)}</span>
                                  <span className="text-slate-300">/</span>
                                  <span className="text-emerald-600">{student.effortScore.toFixed(1)}</span>
                                </div>
                                <p className="text-[11px] text-slate-500">Gap: {student.riskGap > 0 ? "+" : ""}{student.riskGap}</p>
                              </div>
                            </td>
                            <td className="px-6 py-4 text-slate-500 text-[13px]">
                              <div className="flex items-center gap-1.5">
                                <Clock className="w-3.5 h-3.5" />
                                {formatDateTime(student.endedAt)}
                              </div>
                            </td>
                            <td className="px-6 py-4 text-right">
                              <div className="flex items-center justify-end gap-2">
                                <button
                                  onClick={() => navigate(`/student/${student.studentId}`)}
                                  className="inline-flex items-center rounded-lg border border-slate-200 px-3 py-1.5 text-sm font-medium text-slate-700 hover:bg-slate-50 hover:border-indigo-200 hover:text-indigo-600 transition-colors bg-white shadow-sm active:scale-95"
                                >
                                  Student Detail
                                </button>
                                <button
                                  onClick={() => navigate(`/sessions/${student.sessionId}`)}
                                  className="inline-flex items-center rounded-lg border border-slate-200 px-3 py-1.5 text-sm font-medium text-slate-700 hover:bg-slate-50 hover:border-indigo-200 hover:text-indigo-600 transition-colors bg-white shadow-sm active:scale-95"
                                >
                                  Session Detail
                                </button>
                              </div>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              </div>

              <div className="p-6 border-t border-slate-100 bg-slate-50/50 flex flex-col sm:flex-row sm:items-center justify-between gap-3 shrink-0">
                <button
                  onClick={() => setSelectedAlert(null)}
                  className="px-5 py-2.5 bg-white border border-slate-200 text-slate-700 font-medium rounded-xl hover:bg-slate-50 transition-colors shadow-sm active:scale-95"
                >
                  Close
                </button>
                <div className="flex flex-wrap items-center gap-3 justify-end">
                  {selectedAlert.proctorSessionId && (
                    <button
                      onClick={() => openExamSession(selectedAlert)}
                      className="inline-flex items-center justify-center px-5 py-2.5 bg-white border border-slate-200 text-slate-700 font-medium rounded-xl hover:bg-slate-50 transition-colors shadow-sm active:scale-95"
                    >
                      Open Exam Session
                      <ChevronRight className="w-4 h-4 ml-2" />
                    </button>
                  )}
                  {selectedAlert.status === "unresolved" ? (
                    <button
                      onClick={() => {
                        handleResolve(selectedAlert.id);
                        setSelectedAlert(null);
                      }}
                      className="inline-flex items-center justify-center px-5 py-2.5 bg-emerald-600 text-white font-semibold rounded-xl hover:bg-emerald-700 transition-all shadow-sm active:scale-95"
                    >
                      <Check className="w-4 h-4 mr-2" />
                      Mark Resolved
                    </button>
                  ) : (
                    <div className="inline-flex items-center justify-center px-5 py-2.5 bg-emerald-50 text-emerald-700 font-semibold rounded-xl border border-emerald-200">
                      <Check className="w-4 h-4 mr-2" />
                      Resolved
                    </div>
                  )}
                </div>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </div>
  );
}