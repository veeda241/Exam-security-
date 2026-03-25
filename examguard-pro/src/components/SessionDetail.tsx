import { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { motion, AnimatePresence } from "motion/react";
import { ArrowLeft, Camera, Layout, ShieldAlert, Activity, FileText, Download, Loader2, Users, AlertTriangle, CheckCircle2 } from "lucide-react";

// Mock students data for the session
const mockStudents = Array.from({ length: 12 }).map((_, i) => ({
  id: `STU-00${i + 1}`,
  name: ["Alice Johnson", "Bob Smith", "Charlie Davis", "Diana Evans", "Ethan Hunt", "Fiona Gallagher", "George Miller", "Hannah Abbott", "Ian Wright", "Julia Roberts", "Kevin Hart", "Laura Palmer"][i],
  status: Math.random() > 0.8 ? 'flagged' : 'active',
  riskScore: Math.floor(Math.random() * 100),
  effortScore: Math.floor(Math.random() * 100),
}));

export function SessionDetail() {
  const { sessionId } = useParams();
  const navigate = useNavigate();
  
  const [isEnded, setIsEnded] = useState(false);
  const [feedModes, setFeedModes] = useState<Record<string, 'camera' | 'screen'>>({});
  const [refreshKey, setRefreshKey] = useState(Date.now());
  const [isGeneratingPdf, setIsGeneratingPdf] = useState(false);
  const [isPdfGenerated, setIsPdfGenerated] = useState(false);

  // Auto-refresh feeds every 5 seconds
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

  const handleDownloadPdf = () => {
    setIsGeneratingPdf(true);
    setTimeout(() => {
      setIsGeneratingPdf(false);
      setIsPdfGenerated(true);
      setTimeout(() => setIsPdfGenerated(false), 3000);
    }, 2000);
  };

  const avgRisk = Math.round(mockStudents.reduce((acc, s) => acc + s.riskScore, 0) / mockStudents.length);
  const avgEffort = Math.round(mockStudents.reduce((acc, s) => acc + s.effortScore, 0) / mockStudents.length);
  const flaggedCount = mockStudents.filter(s => s.status === 'flagged').length;

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
              <h1 className="text-2xl font-bold text-slate-900 tracking-tight">{sessionId}</h1>
              <span className={`inline-flex items-center px-2.5 py-1 rounded-md text-xs font-semibold border ${
                isEnded ? 'bg-slate-100 text-slate-700 border-slate-200' : 'bg-emerald-50 text-emerald-700 border-emerald-200 animate-pulse'
              }`}>
                {isEnded ? 'Completed' : 'Live'}
              </span>
            </div>
            <p className="text-sm text-slate-500 mt-1">CS101 Midterm • Computer Science</p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          {!isEnded ? (
            <button 
              onClick={() => setIsEnded(true)}
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
        {!isEnded ? (
          <motion.div 
            key="live-grid"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
            className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4"
          >
            {mockStudents.map((student) => {
              const mode = feedModes[student.id] || 'camera';
              return (
                <div 
                  key={student.id} 
                  onClick={() => toggleFeedMode(student.id)}
                  className={`relative bg-slate-900 rounded-2xl overflow-hidden aspect-video cursor-pointer group shadow-sm border-2 transition-colors ${
                    student.status === 'flagged' ? 'border-rose-500' : 'border-transparent hover:border-indigo-400'
                  }`}
                >
                  <img 
                    src={`https://picsum.photos/seed/${student.id}-${mode}-${refreshKey}/400/300`}
                    alt={`${student.name} feed`}
                    className="w-full h-full object-cover opacity-90 group-hover:opacity-100 transition-opacity"
                    referrerPolicy="no-referrer"
                  />
                  
                  {/* Overlays */}
                  <div className="absolute inset-0 bg-gradient-to-t from-slate-900/80 via-transparent to-slate-900/30 pointer-events-none" />
                  
                  <div className="absolute top-3 left-3 flex items-center gap-2">
                    <div className="bg-slate-900/60 backdrop-blur-md text-white text-xs px-2 py-1 rounded-md font-medium flex items-center gap-1.5">
                      {mode === 'camera' ? <Camera className="w-3 h-3" /> : <Layout className="w-3 h-3" />}
                      {student.name}
                    </div>
                  </div>

                  {student.status === 'flagged' && (
                    <div className="absolute top-3 right-3 bg-rose-500 text-white text-[10px] font-bold px-2 py-1 rounded-md uppercase tracking-wider animate-pulse shadow-sm">
                      Flagged
                    </div>
                  )}

                  <div className="absolute bottom-3 left-3 right-3 flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <div className={`px-2 py-1 rounded-md text-[10px] font-bold uppercase tracking-wider backdrop-blur-md ${
                        student.riskScore > 70 ? 'bg-rose-500/80 text-white' : 
                        student.riskScore > 30 ? 'bg-amber-500/80 text-white' : 
                        'bg-emerald-500/80 text-white'
                      }`}>
                        Risk: {student.riskScore}
                      </div>
                    </div>
                    <div className="bg-slate-900/60 backdrop-blur-md text-white text-[10px] px-2 py-1 rounded-md font-mono flex items-center gap-1.5">
                      <span className="w-1.5 h-1.5 rounded-full bg-rose-500 animate-pulse"></span>
                      LIVE
                    </div>
                  </div>

                  {/* Hover Instruction */}
                  <div className="absolute inset-0 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity bg-slate-900/40 backdrop-blur-[2px]">
                    <div className="bg-white/90 text-slate-900 text-xs font-semibold px-3 py-1.5 rounded-full shadow-lg flex items-center gap-2">
                      <ArrowLeft className="w-3 h-3" />
                      Switch to {mode === 'camera' ? 'Screen' : 'Camera'}
                    </div>
                  </div>
                </div>
              );
            })}
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
                  <p className="text-sm font-semibold text-slate-500 uppercase tracking-wider">Total Anomalies</p>
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
                      <th className="px-6 py-4 font-semibold text-xs uppercase tracking-wider">Anomalies</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {mockStudents.map((student) => (
                      <tr key={student.id} className="hover:bg-slate-50/80 transition-colors bg-white">
                        <td className="px-6 py-4">
                          <div className="flex items-center gap-3">
                            <div className="w-8 h-8 rounded-full bg-indigo-100 text-indigo-700 flex items-center justify-center font-bold text-xs border border-indigo-200">
                              {student.name.split(' ').map(n => n[0]).join('')}
                            </div>
                            <div>
                              <p className="font-medium text-slate-900">{student.name}</p>
                              <p className="text-xs text-slate-500">{student.id}</p>
                            </div>
                          </div>
                        </td>
                        <td className="px-6 py-4">
                          <div className="flex items-center gap-2">
                            <div className="w-full bg-slate-100 rounded-full h-2 max-w-[100px]">
                              <div 
                                className={`h-2 rounded-full ${student.riskScore > 70 ? 'bg-rose-500' : student.riskScore > 30 ? 'bg-amber-500' : 'bg-emerald-500'}`} 
                                style={{ width: `${student.riskScore}%` }}
                              />
                            </div>
                            <span className="font-medium text-slate-700">{student.riskScore}</span>
                          </div>
                        </td>
                        <td className="px-6 py-4">
                          <div className="flex items-center gap-2">
                            <div className="w-full bg-slate-100 rounded-full h-2 max-w-[100px]">
                              <div 
                                className="h-2 rounded-full bg-indigo-500" 
                                style={{ width: `${student.effortScore}%` }}
                              />
                            </div>
                            <span className="font-medium text-slate-700">{student.effortScore}</span>
                          </div>
                        </td>
                        <td className="px-6 py-4">
                          {student.status === 'flagged' ? (
                            <span className="inline-flex items-center px-2 py-1 rounded-md text-[10px] font-semibold uppercase tracking-wider bg-rose-50 text-rose-700 border border-rose-200">
                              Flagged
                            </span>
                          ) : (
                            <span className="inline-flex items-center px-2 py-1 rounded-md text-[10px] font-semibold uppercase tracking-wider bg-slate-100 text-slate-500 border border-slate-200">
                              None
                            </span>
                          )}
                        </td>
                      </tr>
                    ))}
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
