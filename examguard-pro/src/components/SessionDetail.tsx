import { useState, useEffect, useCallback, useRef } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { motion, AnimatePresence } from "motion/react";
import { ArrowLeft, Camera, ShieldAlert, Activity, Download, Loader2, Users, AlertTriangle, CheckCircle2, RefreshCw, Eye, Monitor } from "lucide-react";
import { config } from "../config";
import { useWebSocket } from "../hooks/useWebSocket";

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
  
  const [students, setStudents] = useState<StudentSession[]>([]);
  const [loading, setLoading] = useState(true);
  const [isEnded, setIsEnded] = useState(false);
  const [examId, setExamId] = useState<string | null>(null);
  const [refreshKey, setRefreshKey] = useState(Date.now());
  const [selectedStudent, setSelectedStudent] = useState<string | null>(null);
  const [isGeneratingPdf, setIsGeneratingPdf] = useState(false);
  const [isPdfGenerated, setIsPdfGenerated] = useState(false);

  // Object storing the latest base64 data URL for each student/mode (fallback)
  const [liveFrames, setLiveFrames] = useState<Record<string, { webcam?: string, screenshot?: string }>>({});

  const subscribedSessionsRef = useRef<Set<string>>(new Set());

  const handleWebSocketMessage = useCallback((lastEvent: any) => {
    const eventType = lastEvent.type || lastEvent.event_type;
    
    if (eventType === 'student_joined' || eventType === 'STUDENT_JOINED') {
      const newStudent = lastEvent.data;
      if (newStudent) {
        setStudents(prev => {
          const exists = prev.find(s => s.id === newStudent.id);
          if (exists) {
             return prev.map(s => s.id === newStudent.id ? { ...s, status: 'active' } : s);
          }
          return [...prev, {
            ...newStudent,
            risk_score: newStudent.risk_score || 0,
            engagement_score: newStudent.engagement_score || 100,
            effort_alignment: newStudent.effort_alignment || 100,
            risk_level: newStudent.risk_level || 'safe',
            status: 'active',
            started_at: newStudent.started_at || new Date().toISOString(),
          }];
        });
      }
    } else if (eventType === 'student_left' || eventType === 'STUDENT_LEFT') {
      const leftStudentId = lastEvent.student_id || lastEvent.data?.student_id;
      if (leftStudentId) {
        setStudents(prev => prev.map(s => 
          (s.student_id === leftStudentId || s.id === leftStudentId) 
            ? { ...s, status: 'ended' } 
            : s
        ));
      }
    } else if (eventType === 'live_frame') {
      const { student_id, frame_type, data } = lastEvent;
      if (student_id && frame_type && data) {
        setLiveFrames(prev => ({
          ...prev,
          [student_id]: {
            ...(prev[student_id] || {}),
            [frame_type]: data
          }
        }));
      }
    }
  }, []);

  // WebSocket for live student arrivals and video transmissions
  const { messages: liveEvents, sendMessage, isConnected } = useWebSocket(sessionId || examId || undefined, handleWebSocketMessage);

  useEffect(() => {
    if (isConnected && students.length > 0) {
      students.filter(student => student?.id && isLiveStudent(student)).forEach(student => {
        // Only subscribe if not already subscribed
        if (!subscribedSessionsRef.current.has(student.id)) {
          sendMessage(`subscribe:${student.id}`);
          subscribedSessionsRef.current.add(student.id);
        }
      });
    }
  }, [isConnected, students, sendMessage]);

  useEffect(() => {
    if (isConnected && examId) {
      sendMessage(`subscribe:${examId}`);
    }
  }, [isConnected, examId, sendMessage]);

  // Fetch all sessions for this exam
  const fetchSessions = useCallback(async () => {
    try {
      const res = await fetch(`${config.apiUrl}/sessions?active_only=false&limit=200`);
      if (res.ok) {
        const data = await res.json();
        let currentSession = data.find((s: any) => s.id === sessionId);
        
        // Fallback: if session not found in bulk list, fetch it individually
        if (!currentSession) {
          try {
            const singleRes = await fetch(`${config.apiUrl}/sessions/${sessionId}`);
            if (singleRes.ok) {
              currentSession = await singleRes.json();
            }
          } catch {
            console.warn('Failed to fetch individual session');
          }
        }
        
        if (currentSession) {
          const currentExamId = currentSession.exam_id;
          setExamId(currentExamId);
          
          // Get all student sessions for this exam (exclude PROCTOR sessions)
          const studentSessions = data.filter(
            (s: any) => s.exam_id === currentExamId && !s.student_id?.startsWith('PROCTOR-')
          );
          
          setStudents(studentSessions);
          
          // Sessions can have status 'recording' or 'active' when live
          const isSessionActive = currentSession.status === 'active' || currentSession.status === 'recording' || currentSession.is_active === true;
          setIsEnded(!isSessionActive);
        }
      }
    } catch (e) {
      console.error("Failed to fetch sessions:", e);
    } finally {
      setLoading(false);
    }
  }, [sessionId]);

  useEffect(() => {
    fetchSessions();
  }, [fetchSessions]);

  // Auto-refresh data periodically (but NOT feeds, those are strictly WebSocket-driven now)
  useEffect(() => {
    if (isEnded) return;
    // Re-fetch session data for scores less frequently
    const dataInterval = setInterval(() => {
      fetchSessions();
    }, 15000);
    return () => {
      clearInterval(dataInterval);
    };
  }, [isEnded, fetchSessions]);

  const handleEndSession = async () => {
    try {
      if (confirm("End this proctoring session?")) {
        await fetch(`${config.apiUrl}/sessions/${sessionId}/end`, { method: 'POST' });
        setIsEnded(true);
        setRefreshKey(Date.now());
      }
    } catch (e) {
      console.error("Failed to end session:", e);
    }
  };

  const handleDownloadPdf = async () => {
    setIsGeneratingPdf(true);
    try {
      // Call the real backend report generator
      const res = await fetch(`${config.apiUrl}/reports/session/${sessionId}/pdf`);
      if (!res.ok) throw new Error(`PDF generation failed (${res.status})`);

      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `report_${examId || sessionId?.substring(0, 8)}.pdf`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);

      setIsPdfGenerated(true);
      setTimeout(() => setIsPdfGenerated(false), 3000);
    } catch (err) {
      console.error('PDF download error:', err);
      alert('Failed to generate PDF report. Please try again.');
    } finally {
      setIsGeneratingPdf(false);
    }
  };

  const getStudentName = (s: StudentSession) => s.student_name || s.student_id;
  const getInitials = (name?: string) => (name || 'U').split(' ').map(n => n[0]).join('').toUpperCase().slice(0, 2);

  const avgRisk = students.length > 0
    ? Math.round(students.reduce((acc, s) => acc + (s.risk_score || 0), 0) / students.length)
    : 0;
  const avgEffort = students.length > 0
    ? Math.round(students.reduce((acc, s) => acc + (s.engagement_score || s.effort_alignment || 0), 0) / students.length)
    : 0;
  const flaggedCount = students.filter(s => s.risk_level === 'review' || s.risk_level === 'suspicious').length;
  const isLiveStudent = (student: StudentSession) => {
    const status = (student.status || '').toLowerCase();
    return student.is_active === true || status === 'active' || status === 'recording';
  };
  const resolveSessionFeedId = (student: StudentSession) => student.id || student.student_id;

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
              <h1 className="text-2xl font-bold text-slate-900 tracking-tight">
                {examId || sessionId?.substring(0, 8).toUpperCase()}
              </h1>
              <span className={`inline-flex items-center px-2.5 py-1 rounded-md text-xs font-semibold border ${
                isEnded ? 'bg-slate-100 text-slate-700 border-slate-200' : 'bg-emerald-50 text-emerald-700 border-emerald-200 animate-pulse'
              }`}>
                {isEnded ? 'Completed' : '● Live'}
              </span>
            </div>
            <p className="text-sm text-slate-500 mt-1">
              {students.length} student{students.length !== 1 ? 's' : ''} connected
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
              {isGeneratingPdf ? "Generating PDF..." : isPdfGenerated ? "Downloaded" : "Download Report"}
            </button>
          )}
        </div>
      </div>

      {/* Summary Stats (show when live) */}
      {!isEnded && students.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm flex items-center gap-4">
            <div className="p-3 rounded-xl bg-indigo-50 text-indigo-600">
              <ShieldAlert className="w-6 h-6" />
            </div>
            <div>
              <p className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider">Avg Risk</p>
              <p className={`text-2xl font-bold ${avgRisk > 70 ? 'text-rose-600' : avgRisk > 30 ? 'text-amber-500' : 'text-emerald-600'}`}>
                {avgRisk}<span className="text-sm text-slate-400 font-medium">/100</span>
              </p>
            </div>
          </div>
          <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm flex items-center gap-4">
            <div className="p-3 rounded-xl bg-emerald-50 text-emerald-600">
              <Activity className="w-6 h-6" />
            </div>
            <div>
              <p className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider">Avg Effort</p>
              <p className="text-2xl font-bold text-slate-900">
                {avgEffort}<span className="text-sm text-slate-400 font-medium">/100</span>
              </p>
            </div>
          </div>
          <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm flex items-center gap-4">
            <div className="p-3 rounded-xl bg-rose-50 text-rose-600">
              <AlertTriangle className="w-6 h-6" />
            </div>
            <div>
              <p className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider">Flagged</p>
              <p className="text-2xl font-bold text-slate-900">{flaggedCount}</p>
            </div>
          </div>
        </div>
      )}

      {/* MAIN CONTENT: Live student feed grid */}
      <AnimatePresence mode="wait">
        {students.length > 0 ? (
          <motion.div 
            key="student-feeds"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
            className="space-y-6"
          >
            {/* Student Feeds Grid */}
            <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
              <div className="p-5 border-b border-slate-200 bg-slate-50/50 flex items-center justify-between">
                <h2 className="text-lg font-bold text-slate-900 flex items-center gap-2">
                  <Eye className="w-5 h-5 text-indigo-500" />
                  Live Student Feeds
                </h2>
                <button 
                  onClick={() => setRefreshKey(Date.now())}
                  className="p-2 text-slate-400 hover:text-indigo-600 hover:bg-indigo-50 rounded-xl transition-colors"
                  title="Refresh feeds"
                >
                  <RefreshCw className="w-4 h-4" />
                </button>
              </div>
              
              <div className="p-5">
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
                  {students.filter(s => s?.id).map((student) => {
                    const studentId = resolveSessionFeedId(student) || student.id;  // Use consistent ID
                    const name = getStudentName(student);
                    const riskScore = student.risk_score || 0;
                    const effortScore = student.engagement_score || student.effort_alignment || 0;
                    const isFlagged = student.risk_level === 'review' || student.risk_level === 'suspicious';
                    const isSelected = selectedStudent === studentId;

                    const webcamFrame = liveFrames[studentId]?.webcam || liveFrames[student.student_id]?.webcam;
                    const screenFrame = liveFrames[studentId]?.screenshot || liveFrames[student.student_id]?.screenshot;
                    const webcamFeedUrl = webcamFrame || (isLiveStudent(student) && studentId ? `${config.apiUrl}/uploads/latest/${studentId}?type=webcam&t=${refreshKey}` : null);
                    const screenFeedUrl = screenFrame || (isLiveStudent(student) && studentId ? `${config.apiUrl}/uploads/latest/${studentId}?type=screenshot&t=${refreshKey}` : null);

                    return (
                      <motion.div
                        key={studentId}
                        initial={{ opacity: 0, scale: 0.95 }}
                        animate={{ opacity: 1, scale: 1 }}
                        className={`relative rounded-2xl overflow-hidden shadow-md border-2 transition-all ${
                          isSelected ? 'ring-4 ring-indigo-400/30 border-indigo-400' :
                          isFlagged ? 'border-rose-400 ring-4 ring-rose-400/20' : 'border-slate-200 hover:border-slate-300'
                        }`}
                      >
                        {/* Feed Display */}
                        <div className="p-3 bg-slate-950/95 space-y-3">
                          <div className="relative bg-slate-900 aspect-video overflow-hidden rounded-xl">
                            {webcamFeedUrl ? (
                              <img
                                src={webcamFeedUrl}
                                alt={`${name} webcam snapshot`}
                                className="w-full h-full object-cover"
                              />
                            ) : (
                              <div className="absolute inset-0 flex flex-col items-center justify-center bg-slate-800 text-slate-400">
                                <Camera className="w-10 h-10 mb-2 opacity-30" />
                                <span className="text-xs opacity-50">
                                  {isLiveStudent(student) ? 'Waiting for webcam feed...' : 'No live webcam available'}
                                </span>
                              </div>
                            )}

                            <div className="absolute inset-0 bg-gradient-to-t from-slate-900/80 via-transparent to-slate-900/30 pointer-events-none" />

                            <div className="absolute top-3 left-3 flex items-center gap-2">
                              <div className="bg-slate-900/60 backdrop-blur-md text-white text-xs px-2.5 py-1 rounded-lg font-medium flex items-center gap-1.5 border border-white/10">
                                <Camera className="w-3 h-3" />
                                Webcam
                              </div>
                            </div>

                            {isFlagged && (
                              <div className="absolute top-3 right-3 bg-rose-500 text-white text-[10px] font-bold px-2 py-1 rounded-lg uppercase tracking-wider animate-pulse shadow-lg">
                                ⚠ Flagged
                              </div>
                            )}

                            <div className="absolute bottom-3 left-3 right-3 flex items-center justify-between">
                              <div className={`px-2.5 py-1 rounded-lg text-[10px] font-bold uppercase tracking-wider backdrop-blur-md border border-white/10 ${
                                riskScore > 70 ? 'bg-rose-500/80 text-white' :
                                riskScore > 30 ? 'bg-amber-500/80 text-white' :
                                'bg-emerald-500/80 text-white'
                              }`}>
                                Risk: {riskScore}
                              </div>
                              <div className="bg-slate-900/60 backdrop-blur-md text-white text-[10px] px-2 py-1 rounded-lg font-mono flex items-center gap-1.5 border border-white/10">
                                {student.status === 'active' ? (
                                  <>
                                    <span className="w-1.5 h-1.5 rounded-full bg-rose-500 animate-pulse"></span>
                                    LIVE
                                  </>
                                ) : (
                                  <>
                                    <span className="w-1.5 h-1.5 rounded-full bg-slate-500"></span>
                                    OFFLINE
                                  </>
                                )}
                              </div>
                            </div>
                          </div>

                          <div className="relative bg-slate-900 aspect-video overflow-hidden rounded-xl border border-slate-800">
                            {screenFeedUrl ? (
                              <img
                                src={screenFeedUrl}
                                alt={`${name} screen snapshot`}
                                className="w-full h-full object-cover"
                              />
                            ) : (
                              <div className="absolute inset-0 flex flex-col items-center justify-center bg-slate-800 text-slate-400">
                                <Monitor className="w-10 h-10 mb-2 opacity-30" />
                                <span className="text-xs opacity-50">
                                  {isLiveStudent(student) ? 'Waiting for screen share...' : 'No live screen available'}
                                </span>
                              </div>
                            )}

                            <div className="absolute inset-0 bg-gradient-to-t from-slate-900/80 via-transparent to-slate-900/30 pointer-events-none" />

                            <div className="absolute top-3 left-3 flex items-center gap-2">
                              <div className="bg-slate-900/60 backdrop-blur-md text-white text-xs px-2.5 py-1 rounded-lg font-medium flex items-center gap-1.5 border border-white/10">
                                <Monitor className="w-3 h-3" />
                                Screen
                              </div>
                            </div>
                          </div>
                        </div>

                        {/* Student Info Bar below the feed */}
                        <div className="bg-white p-3 border-t border-slate-100">
                          <div className="flex items-center justify-between">
                            <div className="flex items-center gap-2.5">
                              <div className="w-8 h-8 rounded-full bg-indigo-50 text-indigo-700 flex items-center justify-center text-[10px] font-bold border border-indigo-100">
                                {getInitials(name)}
                              </div>
                              <div>
                                <p className="text-sm font-semibold text-slate-900 leading-tight">{name}</p>
                                <p className="text-[10px] text-slate-400">{student.student_id}</p>
                              </div>
                            </div>
                            <div className="flex items-center gap-3">
                              {/* Effort bar */}
                              <div className="text-right hidden sm:block">
                                <p className="text-[9px] text-slate-400 uppercase font-semibold">Effort</p>
                                <div className="w-16 h-1.5 bg-slate-100 rounded-full mt-0.5">
                                  <div
                                    className={`h-full rounded-full transition-all duration-1000 ${
                                      effortScore > 70 ? 'bg-emerald-500' : effortScore > 40 ? 'bg-amber-500' : 'bg-rose-500'
                                    }`}
                                    style={{ width: `${effortScore}%` }}
                                  />
                                </div>
                              </div>
                              {/* Risk bar */}
                              <div className="text-right">
                                <p className="text-[9px] text-slate-400 uppercase font-semibold">Risk</p>
                                <div className="w-16 h-1.5 bg-slate-100 rounded-full mt-0.5">
                                  <div
                                    className={`h-full rounded-full transition-all duration-1000 ${
                                      riskScore > 70 ? 'bg-rose-500' : riskScore > 30 ? 'bg-amber-500' : 'bg-emerald-500'
                                    }`}
                                    style={{ width: `${riskScore}%` }}
                                  />
                                </div>
                              </div>
                            </div>
                          </div>
                        </div>
                      </motion.div>
                    );
                  })}
                </div>
              </div>
            </div>

            {/* Student Performance Table (below feeds) */}
            {isEnded && (
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
                      {students.map((student) => {
                        const name = getStudentName(student);
                        const riskScore = student.risk_score || 0;
                        const effortScore = student.engagement_score || student.effort_alignment || 0;
                        const isFlagged = student.risk_level === 'review' || student.risk_level === 'suspicious';
                        return (
                          <tr key={student.id} className="hover:bg-slate-50/80 transition-colors bg-white">
                            <td className="px-6 py-4">
                              <div className="flex items-center gap-3">
                                <div className="w-10 h-10 rounded-full bg-indigo-50 text-indigo-700 flex items-center justify-center font-bold text-xs border border-indigo-100 shadow-sm">
                                  {getInitials(name)}
                                </div>
                                <div>
                                  <p className="font-bold text-slate-900">{name}</p>
                                  <p className="text-xs text-slate-500">{student.student_id}</p>
                                </div>
                              </div>
                            </td>
                            <td className="px-6 py-4">
                              <div className="flex items-center gap-3">
                                <div className="w-full bg-slate-100 rounded-full h-2 max-w-[120px]">
                                  <div
                                    className={`h-2 rounded-full transition-all duration-1000 ${riskScore > 70 ? 'bg-rose-500' : riskScore > 30 ? 'bg-amber-500' : 'bg-emerald-500'}`}
                                    style={{ width: `${riskScore}%` }}
                                  />
                                </div>
                                <span className="font-bold text-slate-700">{riskScore}</span>
                              </div>
                            </td>
                            <td className="px-6 py-4">
                              <div className="flex items-center gap-3">
                                <div className="w-full bg-slate-100 rounded-full h-2 max-w-[120px]">
                                  <div
                                    className="h-2 rounded-full bg-indigo-500 transition-all duration-1000"
                                    style={{ width: `${effortScore}%` }}
                                  />
                                </div>
                                <span className="font-bold text-slate-700">{effortScore}</span>
                              </div>
                            </td>
                            <td className="px-6 py-4 text-right">
                              {isFlagged ? (
                                <span className="inline-flex items-center px-3 py-1 rounded-full text-[10px] font-bold uppercase tracking-wider bg-rose-50 text-rose-700 border border-rose-100">
                                  Flagged
                                </span>
                              ) : (
                                <span className="inline-flex items-center px-3 py-1 rounded-full text-[10px] font-bold uppercase tracking-wider bg-emerald-50 text-emerald-700 border border-emerald-100">
                                  Safe
                                </span>
                              )}
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </motion.div>
        ) : (
          <motion.div
            key="empty"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="bg-white rounded-2xl border border-slate-200 shadow-sm p-16 text-center"
          >
            <div className="w-16 h-16 bg-slate-50 text-slate-300 rounded-full flex items-center justify-center mx-auto mb-6">
              <Users className="w-8 h-8" />
            </div>
            <h3 className="text-xl font-bold text-slate-900">Waiting for students...</h3>
            <p className="text-slate-500 mt-2 max-w-sm mx-auto">
              The session is active. Share the exam code <strong className="text-indigo-600">{examId}</strong> with students.
              Once they start proctoring, their webcam and screen snapshots will appear here automatically.
            </p>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
