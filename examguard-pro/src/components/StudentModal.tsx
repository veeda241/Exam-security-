import { X, Monitor, Globe, Activity, ShieldAlert, Send, CheckCircle2, Camera, FileText, Loader2, Download, Layout } from "lucide-react";
import { motion, AnimatePresence } from "motion/react";
import { useState, useEffect } from "react";

export function StudentModal({ isOpen, onClose, student }: { isOpen: boolean, onClose: () => void, student?: any }) {
  const [warningSent, setWarningSent] = useState(false);
  const [isGenerating, setIsGenerating] = useState(false);
  const [isGenerated, setIsGenerated] = useState(false);
  const [refreshKey, setRefreshKey] = useState(Date.now());

  useEffect(() => {
    if (!isOpen) return;
    const interval = setInterval(() => {
      setRefreshKey(Date.now());
    }, 5000);
    return () => clearInterval(interval);
  }, [isOpen]);

  const handleSendWarning = () => {
    setWarningSent(true);
    setTimeout(() => setWarningSent(false), 3000);
  };

  const handleGenerateReport = () => {
    setIsGenerating(true);
    setTimeout(() => {
      setIsGenerating(false);
      setIsGenerated(true);
      setTimeout(() => setIsGenerated(false), 4000);
    }, 1500);
  };

  if (!student) return null;

  // Mock detailed data based on the student
  const sitesVisited = [
    { url: "canvas.university.edu/exam", time: "Active", allowed: true },
    { url: "google.com/search?q=calculus+formulas", time: "2 mins ago", allowed: false },
    { url: "mathway.com", time: "5 mins ago", allowed: false },
  ];

  const effectScore = student.riskScore > 70 ? "High Impact" : student.riskScore > 30 ? "Medium Impact" : "Low Impact";

  return (
    <AnimatePresence>
      {isOpen && (
        <div className="fixed inset-0 bg-slate-900/50 backdrop-blur-sm flex items-center justify-center z-50 p-4">
          <motion.div
            initial={{ opacity: 0, scale: 0.95, y: 10 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: 10 }}
            className="bg-white p-0 rounded-2xl w-[900px] max-w-full shadow-xl flex flex-col overflow-hidden max-h-[90vh]"
          >
            {/* Header */}
            <div className="flex items-center justify-between p-6 border-b border-slate-100 bg-slate-50/50 shrink-0">
              <div className="flex items-center gap-4">
                <div className="w-12 h-12 rounded-full bg-indigo-100 text-indigo-700 flex items-center justify-center font-bold text-lg border border-indigo-200 shadow-sm">
                  {student.name.split(' ').map((n: string) => n[0]).join('')}
                </div>
                <div>
                  <h2 className="text-xl font-bold text-slate-900 tracking-tight">{student.name}</h2>
                  <p className="text-sm text-slate-500">{student.id} • {student.course}</p>
                </div>
              </div>
              <button onClick={onClose} className="p-2 text-slate-400 hover:text-slate-600 hover:bg-slate-100 rounded-xl transition-colors">
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Content */}
            <div className="p-6 overflow-y-auto space-y-6">
              
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {/* Left: Media Captures */}
                <div className="space-y-6">
                  {/* Camera Capture */}
                  <div className="space-y-3">
                    <h3 className="text-sm font-semibold text-slate-900 flex items-center gap-2">
                      <Camera className="w-4 h-4 text-slate-500" />
                      Live Camera Feed
                    </h3>
                    <div className="bg-slate-100 rounded-xl border border-slate-200 overflow-hidden aspect-video relative shadow-sm">
                      <img 
                        src={`https://picsum.photos/seed/${student.id}-cam-${refreshKey}/600/400`} 
                        alt="Student camera" 
                        className="w-full h-full object-cover"
                        referrerPolicy="no-referrer"
                      />
                      <div className="absolute bottom-2 right-2 bg-slate-900/70 backdrop-blur-md text-white text-[10px] px-2 py-1 rounded-md font-mono flex items-center gap-1.5">
                        <span className="w-1.5 h-1.5 rounded-full bg-rose-500 animate-pulse"></span>
                        LIVE
                      </div>
                      {student.status === 'flagged' && (
                        <div className="absolute top-2 left-2 bg-rose-500 text-white text-[10px] font-bold px-2 py-1 rounded-md uppercase tracking-wider animate-pulse shadow-sm">
                          Anomaly Detected
                        </div>
                      )}
                    </div>
                  </div>

                  {/* Screen Capture */}
                  <div className="space-y-3">
                    <h3 className="text-sm font-semibold text-slate-900 flex items-center gap-2">
                      <Layout className="w-4 h-4 text-slate-500" />
                      Live Screen Feed
                    </h3>
                    <div className="bg-slate-100 rounded-xl border border-slate-200 overflow-hidden aspect-video relative shadow-sm">
                      <img 
                        src={`https://picsum.photos/seed/${student.id}-screen-${refreshKey}/600/400`} 
                        alt="Student screen" 
                        className="w-full h-full object-cover"
                        referrerPolicy="no-referrer"
                      />
                      <div className="absolute bottom-2 right-2 bg-slate-900/70 backdrop-blur-md text-white text-[10px] px-2 py-1 rounded-md font-mono flex items-center gap-1.5">
                        <span className="w-1.5 h-1.5 rounded-full bg-rose-500 animate-pulse"></span>
                        LIVE
                      </div>
                    </div>
                  </div>
                </div>

                {/* Right: Scores & Activity */}
                <div className="space-y-6">
                  {/* Scores */}
                  <div className="grid grid-cols-2 gap-4">
                    <div className="bg-slate-50 rounded-xl p-4 border border-slate-100 flex flex-col justify-center">
                      <div className="flex items-center gap-3 mb-2">
                        <div className={`p-2 rounded-lg ${student.riskScore > 70 ? 'bg-rose-100 text-rose-600' : student.riskScore > 30 ? 'bg-amber-100 text-amber-600' : 'bg-emerald-100 text-emerald-600'}`}>
                          <ShieldAlert className="w-4 h-4" />
                        </div>
                        <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Risk Score</p>
                      </div>
                      <p className={`text-3xl font-bold ${student.riskScore > 70 ? 'text-rose-600' : student.riskScore > 30 ? 'text-amber-600' : 'text-emerald-600'}`}>{student.riskScore}<span className="text-sm text-slate-400 font-medium">/100</span></p>
                    </div>
                    <div className="bg-slate-50 rounded-xl p-4 border border-slate-100 flex flex-col justify-center">
                      <div className="flex items-center gap-3 mb-2">
                        <div className="p-2 rounded-lg bg-indigo-100 text-indigo-600">
                          <Activity className="w-4 h-4" />
                        </div>
                        <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Effect</p>
                      </div>
                      <p className="text-lg font-bold text-slate-900 leading-tight">{effectScore}</p>
                    </div>
                  </div>

                  {/* Current Activity */}
                  <div>
                    <h3 className="text-sm font-semibold text-slate-900 mb-3 flex items-center gap-2">
                      <FileText className="w-4 h-4 text-slate-500" />
                      Current Exam Activity
                    </h3>
                    <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm">
                      <p className="text-sm text-slate-700">
                        <span className="font-medium text-slate-900">Status:</span> Actively taking {student.course} Exam.
                      </p>
                      <p className="text-sm text-slate-700 mt-2">
                        <span className="font-medium text-slate-900">Latest Event:</span> {student.status === 'flagged' ? 'Unusual activity detected (e.g., multiple tabs or looking away)' : 'Normal behavior observed'}.
                      </p>
                    </div>
                  </div>
                </div>
              </div>

              {/* Sites Visited */}
              <div>
                <h3 className="text-sm font-semibold text-slate-900 mb-3 flex items-center gap-2">
                  <Globe className="w-4 h-4 text-slate-500" />
                  Recent Sites Visited
                </h3>
                <div className="border border-slate-200 rounded-xl overflow-hidden shadow-sm">
                  <table className="w-full text-left text-sm">
                    <thead className="bg-slate-50 text-slate-500 border-b border-slate-200">
                      <tr>
                        <th className="px-4 py-3 font-medium">URL</th>
                        <th className="px-4 py-3 font-medium">Time</th>
                        <th className="px-4 py-3 font-medium">Status</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100">
                      {sitesVisited.map((site, idx) => (
                        <tr key={idx} className="bg-white">
                          <td className="px-4 py-3 text-slate-700 font-mono text-xs">{site.url}</td>
                          <td className="px-4 py-3 text-slate-500">{site.time}</td>
                          <td className="px-4 py-3">
                            <span className={`inline-flex items-center px-2 py-1 rounded-md text-[10px] font-semibold uppercase tracking-wider ${site.allowed ? 'bg-emerald-50 text-emerald-700' : 'bg-rose-50 text-rose-700'}`}>
                              {site.allowed ? 'Allowed' : 'Blocked'}
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

            </div>

            {/* Footer / Actions */}
            <div className="p-6 border-t border-slate-100 bg-slate-50/50 flex flex-col sm:flex-row items-center justify-between gap-4 shrink-0">
              <button 
                onClick={handleGenerateReport}
                disabled={isGenerating || isGenerated}
                className={`w-full sm:w-auto inline-flex items-center justify-center px-4 py-2.5 bg-white border border-slate-200 font-medium rounded-xl transition-colors shadow-sm active:scale-95 ${
                  isGenerated ? 'text-indigo-600 border-indigo-200 bg-indigo-50' : 'text-slate-700 hover:bg-slate-50'
                }`}
              >
                {isGenerating ? (
                  <Loader2 className="w-4 h-4 mr-2 animate-spin text-slate-400" />
                ) : isGenerated ? (
                  <Download className="w-4 h-4 mr-2" />
                ) : (
                  <FileText className="w-4 h-4 mr-2 text-slate-400" />
                )}
                {isGenerating ? "Generating..." : isGenerated ? "Download Document" : "Create Review Document"}
              </button>
              
              <div className="flex items-center gap-3 w-full sm:w-auto">
                <button onClick={onClose} className="flex-1 sm:flex-none px-5 py-2.5 bg-white border border-slate-200 text-slate-700 font-medium rounded-xl hover:bg-slate-50 transition-colors shadow-sm active:scale-95">
                  Close
                </button>
                <button 
                  onClick={handleSendWarning}
                  disabled={warningSent}
                  className={`flex-1 sm:flex-none inline-flex items-center justify-center px-5 py-2.5 font-semibold rounded-xl transition-all shadow-sm active:scale-95 ${
                    warningSent 
                      ? 'bg-emerald-500 text-white' 
                      : 'bg-rose-600 text-white hover:bg-rose-700'
                  }`}
                >
                  {warningSent ? (
                    <>
                      <CheckCircle2 className="w-4 h-4 mr-2" />
                      Warning Sent
                    </>
                  ) : (
                    <>
                      <Send className="w-4 h-4 mr-2" />
                      Send Warning
                    </>
                  )}
                </button>
              </div>
            </div>
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  );
}
