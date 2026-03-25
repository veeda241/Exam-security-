import { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { motion, AnimatePresence } from "motion/react";
import { ArrowLeft, Camera, Layout, ShieldAlert, Activity, Download, Loader2, Users, AlertTriangle, CheckCircle2 } from "lucide-react";
import { config } from "../config";

interface StudentSession {
  id: string;
  student_id: string;
  student_name?: string;
  exam_id: string;
  risk_score: number;
  engagement_score: number;
  effort_alignment: number;
  risk_level: string;
  status: string;
  is_active: boolean;
  started_at: string;
}

export function SessionDetail() {
  const { sessionId } = useParams();
  const navigate = useNavigate();
  
  const [sessions, setSessions] = useState<StudentSession[]>([]);
  const [loading, setLoading] = useState(true);
  const [isEnded, setIsEnded] = useState(false);
  const [feedModes, setFeedModes] = useState<Record<string, 'camera' | 'screen'>>({});
  const [refreshKey, setRefreshKey] = useState(Date.now());
  const [isGeneratingPdf, setIsGeneratingPdf] = useState(false);
  const [isPdfGenerated, setIsPdfGenerated] = useState(false);

  // Fetch real session data
  useEffect(() => {
    const fetchSessions = async () => {
      try {
        const res = await fetch(`${config.apiUrl}/sessions/?active_only=false&limit=100`);
        if (res.ok) {
          const data = await res.json();
          // Find the proctor session to get the exam_id
          const currentSession = data.find((s: any) => s.id === sessionId);
          if (currentSession) {
            const examId = currentSession.exam_id;
            // Get all student sessions for this exam (exclude PROCTOR sessions)
            const studentSessions = data.filter(
              (s: any) => s.exam_id === examId && !s.student_id?.startsWith('PROCTOR-')
            );
            setSessions(studentSessions);
            // Check if the proctor session is still active
            setIsEnded(!currentSession.is_active);
          }
        }
      } catch (e) {
        console.error("Failed to fetch sessions:", e);
      } finally {
        setLoading(false);
      }
    };
    fetchSessions();
  }, [sessionId, refreshKey]);

  // Auto-refresh every 5 seconds
  useEffect(() => {
    if (isEnded) return;
    const interval = setInterval(() => {
      setRefreshKey(Date.now());
    }, 5000);
    return () => clearInterval(interval);
  }, [isEnded]);

  const toggleFeedMode = (studentId: string) => {
    setFeedModes(prev => ({
      ...prev,
      [studentId]: prev[studentId] === 'screen' ? 'camera' : 'screen'
    }));
  };

  const handleEndSession = async () => {
    try {
      await fetch(`${config.apiUrl}/sessions/${sessionId}/end`, { method: 'POST' });
      setIsEnded(true);
      setRefreshKey(Date.now());
    } catch (e) {
      console.error("Failed to end session:", e);
    }
  };

  const handleDownloadPdf = () => {
    setIsGeneratingPdf(true);
    setTimeout(() => {
      setIsGeneratingPdf(false);
      setIsPdfGenerated(true);
      setTimeout(() => setIsPdfGenerated(false), 3000);
    }, 2000);
  };

  const getStudentName = (s: StudentSession) => s.student_name || s.student_id;
  const getInitials = (name: string) => name.split(' ').map(n => n[0]).join('').toUpperCase().slice(0, 2);

  const avgRisk = sessions.length > 0 
    ? Math.round(sessions.reduce((acc, s) => acc + (s.risk_score || 0), 0) / sessions.length) 
    : 0;
  const avgEffort = sessions.length > 0 
    ? Math.round(sessions.reduce((acc, s) => acc + (s.engagement_score || s.effort_alignment || 0), 0) / sessions.length) 
    : 0;
  const flaggedCount = sessions.filter(s => s.risk_level === 'high' || s.risk_level === 'critical').length;

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-8 h-8 animate-spin text-indigo-500" />
      </div>
    );
  }

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-20 md:pb-0">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-white p-6 rounded-2xl border border-slate-200 shadow-sm">
        <div className="flex items-center gap-4">
          <button 
            onClick={() => navigate('/sessions')}
            className="p-2 text-slate-400 hover:text-slate-600 hover:bg-slate-100 rounded-xl transition-colors"
          >
            <ArrowLeft className="w-5 h-5" />
          </button>
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-2xl font-bold text-slate-900 tracking-tight">{sessionId?.substring(0, 8).toUpperCase()}</h1>
              <span className={`inline-flex items-center px-2.5 py-1 rounded-md text-xs font-semibold border ${
                isEnded ? 'bg-slate-100 text-slate-700 border-slate-200' : 'bg-emerald-50 text-emerald-700 border-emerald-200 animate-pulse'
              }`}>
                {isEnded ? 'Completed' : 'Live'}
              </span>
            </div>
            <p className="text-sm text-slate-500 mt-1">
              {sessions.length} student{sessions.length !== 1 ? 's' : ''} connected
            </p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          {!isEnded ? (
            <button 
              onClick={handleEndSession}
              className="px-5 py-2.5 bg-rose-600 text-white font-semibold rounded-xl hover:bg-rose-700 transition-colors shadow-sm active:scale-95"
            >
              End Session
            </button>
          ) : (
            <button 
              onClick={handleDownloadPdf}
              disabled={isGeneratingPdf || isPdfGenerated}
              className={`inline-flex items-center justify-center px-5 py-2.5 font-semibold rounded-xl transition-all shadow-sm active:scale-95 ${
                isPdfGenerated 
                  ? 'bg-emerald-50 text-emerald-700 border border-emerald-200' 
                  : 'bg-indigo-600 text-white hover:bg-indigo-700'
              }`}
            >
              {isGeneratingPdf ? (
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
              ) : isPdfGenerated ? (
                <CheckCircle2 className="w-4 h-4 mr-2" />
              ) : (
                <Download className="w-4 h-4 mr-2" />
              )}
              {isGeneratingPdf ? "Generating PDF..." : isPdfGenerated ? "Downloaded" : "Download Complete PDF"}
            </button>
          )}
        </div>
      </div>

      <AnimatePresence mode="wait">
        {!isEnded && sessions.length > 0 ? (
          <motion.div 
            key="live-grid"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
            className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4"
          >
            {sessions.map((student) => {
              const mode = feedModes[student.student_id] || 'camera';
              const name = getStudentName(student);
              const riskScore = student.risk_score || 0;
              const isFlagged = student.risk_level === 'high' || student.risk_level === 'critical';
              return (
                <div 
                  key={student.id} 
                  onClick={() => toggleFeedMode(student.student_id)}
                  className={`relative bg-slate-900 rounded-2xl overflow-hidden aspect-video cursor-pointer group shadow-sm border-2 transition-colors ${
                    isFlagged ? 'border-rose-500' : 'border-transparent hover:border-indigo-400'
                  }`}
                >
                  <img 
                    src={`https://picsum.photos/seed/${student.student_id}-${mode}-${refreshKey}/400/300`}
                    alt={`${name} feed`}
                    className="w-full h-full object-cover opacity-90 group-hover:opacity-100 transition-opacity"
                    referrerPolicy="no-referrer"
                  />
                  
                  <div className="absolute inset-0 bg-gradient-to-t from-slate-900/80 via-transparent to-slate-900/30 pointer-events-none" />
                  
                  <div className="absolute top-3 left-3 flex items-center gap-2">
                    <div className="bg-slate-900/60 backdrop-blur-md text-white text-xs px-2 py-1 rounded-md font-medium flex items-center gap-1.5">
                      {mode === 'camera' ? <Camera className="w-3 h-3" /> : <Layout className="w-3 h-3" />}
                      {name}
                    </div>
                  </div>

                  {isFlagged && (
                    <div className="absolute top-3 right-3 bg-rose-500 text-white text-[10px] font-bold px-2 py-1 rounded-md uppercase tracking-wider animate-pulse shadow-sm">
                      Flagged
                    </div>
                  )}

                  <div className="absolute bottom-3 left-3 right-3 flex items-center justify-between">
                    <div className={`px-2 py-1 rounded-md text-[10px] font-bold uppercase tracking-wider backdrop-blur-md ${
                      riskScore > 70 ? 'bg-rose-500/80 text-white' : 
                      riskScore > 30 ? 'bg-amber-500/80 text-white' : 
                      'bg-emerald-500/80 text-white'
                    }`}>
                      Risk: {riskScore}
                    </div>
                    <div className="bg-slate-900/60 backdrop-blur-md text-white text-[10px] px-2 py-1 rounded-md font-mono flex items-center gap-1.5">
                      <span className="w-1.5 h-1.5 rounded-full bg-rose-500 animate-pulse"></span>
                      {student.is_active ? 'LIVE' : 'ENDED'}
                    </div>
                  </div>
                </div>
              );
            })}
          </motion.div>
        ) : !isEnded && sessions.length === 0 ? (
          <motion.div
            key="empty"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="bg-white rounded-2xl border border-slate-200 shadow-sm p-12 text-center"
          >
            <Users className="w-12 h-12 text-slate-300 mx-auto mb-4" />
            <h3 className="text-lg font-semibold text-slate-900">Waiting for students...</h3>
            <p className="text-sm text-slate-500 mt-2">Share the exam code with students to let them join via the Chrome extension.</p>
          </motion.div>
        ) : (
          <motion.div 
            key="analytics"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="space-y-6"
          >
            {/* Analytics Summary Cards */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm flex items-center gap-4">
                <div className="p-4 rounded-xl bg-indigo-50 text-indigo-600">
                  <ShieldAlert className="w-8 h-8" />
                </div>
                <div>
                  <p className="text-sm font-semibold text-slate-500 uppercase tracking-wider">Avg Risk Score</p>
                  <p className="text-3xl font-bold text-slate-900">{avgRisk}<span className="text-lg text-slate-400 font-medium">/100</span></p>
                </div>
              </div>
              <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm flex items-center gap-4">
                <div className="p-4 rounded-xl bg-emerald-50 text-emerald-600">
                  <Activity className="w-8 h-8" />
                </div>
                <div>
                  <p className="text-sm font-semibold text-slate-500 uppercase tracking-wider">Avg Effort Score</p>
                  <p className="text-3xl font-bold text-slate-900">{avgEffort}<span className="text-lg text-slate-400 font-medium">/100</span></p>
                </div>
              </div>
              <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm flex items-center gap-4">
                <div className="p-4 rounded-xl bg-rose-50 text-rose-600">
                  <AlertTriangle className="w-8 h-8" />
                </div>
                <div>
                  <p className="text-sm font-semibold text-slate-500 uppercase tracking-wider">Flagged Students</p>
                  <p className="text-3xl font-bold text-slate-900">{flaggedCount}</p>
                </div>
              </div>
            </div>

            {/* Detailed Student List */}
            <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
              <div className="p-6 border-b border-slate-200 bg-slate-50/50">
                <h2 className="text-lg font-bold text-slate-900 flex items-center gap-2">
                  <Users className="w-5 h-5 text-slate-500" />
                  Student Performance & Risk Analysis
                </h2>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full text-left text-sm">
                  <thead className="bg-slate-50 text-slate-500 border-b border-slate-200">
                    <tr>
                      <th className="px-6 py-4 font-semibold text-xs uppercase tracking-wider">Student</th>
                      <th className="px-6 py-4 font-semibold text-xs uppercase tracking-wider">Risk Score</th>
                      <th className="px-6 py-4 font-semibold text-xs uppercase tracking-wider">Effort Score</th>
                      <th className="px-6 py-4 font-semibold text-xs uppercase tracking-wider">Status</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {sessions.length === 0 ? (
                      <tr>
                        <td colSpan={4} className="px-6 py-12 text-center text-slate-500">
                          No students joined this session.
                        </td>
                      </tr>
                    ) : (
                      sessions.map((student) => {
                        const name = getStudentName(student);
                        const riskScore = student.risk_score || 0;
                        const effortScore = student.engagement_score || student.effort_alignment || 0;
                        const isFlagged = student.risk_level === 'high' || student.risk_level === 'critical';
                        return (
                          <tr key={student.id} className="hover:bg-slate-50/80 transition-colors bg-white">
                            <td className="px-6 py-4">
                              <div className="flex items-center gap-3">
                                <div className="w-8 h-8 rounded-full bg-indigo-100 text-indigo-700 flex items-center justify-center font-bold text-xs border border-indigo-200">
                                  {getInitials(name)}
                                </div>
                                <div>
                                  <p className="font-medium text-slate-900">{name}</p>
                                  <p className="text-xs text-slate-500">{student.student_id}</p>
                                </div>
                              </div>
                            </td>
                            <td className="px-6 py-4">
                              <div className="flex items-center gap-2">
                                <div className="w-full bg-slate-100 rounded-full h-2 max-w-[100px]">
                                  <div 
                                    className={`h-2 rounded-full ${riskScore > 70 ? 'bg-rose-500' : riskScore > 30 ? 'bg-amber-500' : 'bg-emerald-500'}`} 
                                    style={{ width: `${riskScore}%` }}
                                  />
                                </div>
                                <span className="font-medium text-slate-700">{riskScore}</span>
                              </div>
                            </td>
                            <td className="px-6 py-4">
                              <div className="flex items-center gap-2">
                                <div className="w-full bg-slate-100 rounded-full h-2 max-w-[100px]">
                                  <div 
                                    className="h-2 rounded-full bg-indigo-500" 
                                    style={{ width: `${effortScore}%` }}
                                  />
                                </div>
                                <span className="font-medium text-slate-700">{effortScore}</span>
                              </div>
                            </td>
                            <td className="px-6 py-4">
                              {isFlagged ? (
                                <span className="inline-flex items-center px-2 py-1 rounded-md text-[10px] font-semibold uppercase tracking-wider bg-rose-50 text-rose-700 border border-rose-200">
                                  Flagged
                                </span>
                              ) : (
                                <span className="inline-flex items-center px-2 py-1 rounded-md text-[10px] font-semibold uppercase tracking-wider bg-emerald-50 text-emerald-600 border border-emerald-200">
                                  {student.risk_level || 'Safe'}
                                </span>
                              )}
                            </td>
                          </tr>
                        );
                      })
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
