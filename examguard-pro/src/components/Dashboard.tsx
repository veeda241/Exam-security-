import React, { useState, useEffect } from "react";
import { 
  Users, 
  AlertTriangle, 
  CheckCircle2, 
  Clock,
  Activity,
  Plus,
  X,
  Copy,
  RefreshCw
} from "lucide-react";
import { 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  ResponsiveContainer,
  AreaChart,
  Area
} from "recharts";
import { useNavigate } from "react-router-dom";
import { motion, AnimatePresence } from "motion/react";
import { config } from '../config';
import { useWebSocket } from '../hooks/useWebSocket';

const initialAlerts: any[] = [];
const data: any[] = [];

export function Dashboard() {
  const navigate = useNavigate();
  const [activeCount, setActiveCount] = useState(0);
  const { messages: liveAlerts } = useWebSocket('/dashboard');
  const [isNewSessionModalOpen, setIsNewSessionModalOpen] = useState(false);
  const [sessionName, setSessionName] = useState("");
  const [studentCount, setStudentCount] = useState("");
   const [examCode, setExamCode] = useState("");
  const [isCreating, setIsCreating] = useState(false);
  
  useEffect(() => {
    const fetchStats = async () => {
       try {
         const res = await fetch(`${config.apiUrl}/sessions/active/count`);
         if (res.ok) {
           const data = await res.json();
           setActiveCount(data.active_count);
         }
       } catch (e) {
         console.error("Stats fetch failed");
       }
    };
    fetchStats();
    const interval = setInterval(fetchStats, 5000);
    return () => clearInterval(interval);
  }, []);

  const generateExamCode = () => {
    const chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789";
    let code = "EXAM-";
    for (let i = 0; i < 6; i++) {
      code += chars.charAt(Math.floor(Math.random() * chars.length));
    }
    setExamCode(code);
  };

  const handleOpenModal = () => {
    generateExamCode();
    setSessionName("");
    setStudentCount("");
    setIsNewSessionModalOpen(true);
  };

  const handleCopyCode = () => {
    navigator.clipboard.writeText(examCode);
  };

  const handleCreateSession = async (e: React.FormEvent) => {
    e.preventDefault();
    if (isCreating) return;
    
    setIsCreating(true);
    try {
      const response = await fetch(`${config.apiUrl}/sessions/create`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          student_id: `PROCTOR-${Math.floor(Math.random() * 9999)}`,
          student_name: "Session Monitor",
          exam_id: sessionName || examCode
        })
      });
      if (response.ok) {
        setIsNewSessionModalOpen(false);
        navigate("/sessions");
      }
    } catch (e) {
      console.error("Failed to create session");
    } finally {
      setIsCreating(false);
    }
  };

  const combinedAlerts = [...liveAlerts
    .filter(m => m.student_name && m.event_type) // Only real alerts
    .map(m => ({
      id: Math.random(),
      studentId: m.student_id || "STU-000",
      student: m.student_name,
      type: m.event_type,
      time: "Live",
      severity: m.risk_level === 'suspicious' ? 'high' : 'medium'
    })), ...initialAlerts].slice(0, 5);


  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Dashboard Overview</h1>
          <p className="text-slate-500 mt-1">Real-time overview of active exam sessions.</p>
        </div>
        <div className="flex items-center gap-3 w-full sm:w-auto">
          <button 
            onClick={async () => {
              if (confirm("Are you sure you want to clear ALL live and recorded session data?")) {
                try {
                  const res = await fetch(`${config.apiUrl}/sessions/clear`, { method: 'DELETE' });
                  if (res.ok) {
                    setActiveCount(0);
                    // Force refresh or just assume 0
                  }
                } catch (e) {
                  alert("Failed to clear sessions");
                }
              }
            }}
            className="inline-flex items-center justify-center rounded-xl bg-white border border-slate-200 px-4 py-2.5 text-sm font-semibold text-slate-600 hover:bg-slate-50 transition-colors shadow-sm active:scale-95 flex-1 sm:flex-none"
          >
            Clear All
          </button>
          <button 
            onClick={handleOpenModal}
            className="inline-flex items-center justify-center rounded-xl bg-indigo-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-indigo-700 transition-colors shadow-sm active:scale-95 flex-1 sm:flex-none"
          >
            <Plus className="w-4 h-4 mr-2" />
            New Session
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-4">
        <motion.div 
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="bg-white rounded-2xl border border-slate-200 p-6 shadow-sm relative overflow-hidden group min-h-[140px]"
        >
          <div className="absolute top-0 right-0 -mt-4 -mr-4 w-24 h-24 bg-indigo-50 rounded-full blur-2xl group-hover:bg-indigo-100 transition-colors"></div>
          <div className="flex items-center justify-between relative z-10">
            <div>
              <p className="text-sm font-medium text-slate-500">Active Students</p>
              <p className="text-3xl font-bold text-slate-900 mt-2">{activeCount}</p>
            </div>
            <div className="p-3 bg-indigo-50 border border-indigo-100 rounded-xl shadow-sm">
              <Users className="w-6 h-6 text-indigo-600" />
            </div>
          </div>
          <div className="mt-5 flex items-center text-sm relative z-10">
            <span className="text-emerald-600 font-medium flex items-center bg-emerald-50 px-2 py-0.5 rounded-md">
              <Activity className="w-3.5 h-3.5 mr-1" /> +Live
            </span>
            <span className="text-slate-500 ml-2 text-xs">connected students</span>
          </div>
        </motion.div>

        <motion.div 
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="bg-white rounded-2xl border border-slate-200 p-6 shadow-sm relative overflow-hidden group"
        >
          <div className="absolute top-0 right-0 -mt-4 -mr-4 w-24 h-24 bg-rose-50 rounded-full blur-2xl group-hover:bg-rose-100 transition-colors"></div>
          <div className="flex items-center justify-between relative z-10">
            <div>
              <p className="text-sm font-medium text-slate-500">Live Alerts</p>
              <p className="text-3xl font-bold text-slate-900 mt-2">{liveAlerts.length}</p>
            </div>
            <div className="p-3 bg-rose-50 border border-rose-100 rounded-xl shadow-sm">
              <AlertTriangle className="w-6 h-6 text-rose-600" />
            </div>
          </div>
          <div className="mt-5 flex items-center text-sm relative z-10">
            <span className="text-rose-600 font-medium flex items-center bg-rose-50 px-2 py-0.5 rounded-md">
              <Activity className="w-3.5 h-3.5 mr-1" /> +{liveAlerts.length}
            </span>
            <span className="text-slate-500 ml-2 text-xs">in current window</span>
          </div>
        </motion.div>

        <motion.div 
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
          className="bg-white rounded-2xl border border-slate-200 p-6 shadow-sm relative overflow-hidden group"
        >
          <div className="absolute top-0 right-0 -mt-4 -mr-4 w-24 h-24 bg-emerald-50 rounded-full blur-2xl group-hover:bg-emerald-100 transition-colors"></div>
          <div className="flex items-center justify-between relative z-10">
            <div>
              <p className="text-sm font-medium text-slate-500">Safe Status</p>
              <p className="text-3xl font-bold text-slate-900 mt-2">--%</p>
            </div>
            <div className="p-3 bg-emerald-50 border border-emerald-100 rounded-xl shadow-sm">
              <CheckCircle2 className="w-6 h-6 text-emerald-600" />
            </div>
          </div>
          <div className="mt-5 flex items-center text-sm relative z-10">
            <span className="text-emerald-600 font-medium flex items-center bg-emerald-50 px-2 py-0.5 rounded-md">
              <Activity className="w-3.5 h-3.5 mr-1" /> High
            </span>
            <span className="text-slate-500 ml-2 text-xs">average integrity</span>
          </div>
        </motion.div>

        <motion.div 
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.4 }}
          className="bg-white rounded-2xl border border-slate-200 p-6 shadow-sm relative overflow-hidden group"
        >
          <div className="absolute top-0 right-0 -mt-4 -mr-4 w-24 h-24 bg-blue-50 rounded-full blur-2xl group-hover:bg-blue-100 transition-colors"></div>
          <div className="flex items-center justify-between relative z-10">
            <div>
              <p className="text-sm font-medium text-slate-500">Avg Progress</p>
              <p className="text-3xl font-bold text-slate-900 mt-2">0%</p>
            </div>
            <div className="p-3 bg-blue-50 border border-blue-100 rounded-xl shadow-sm">
              <Clock className="w-6 h-6 text-blue-600" />
            </div>
          </div>
          <div className="mt-5 flex items-center text-sm relative z-10">
            <span className="text-slate-500 text-xs">Across all active exams</span>
          </div>
        </motion.div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        <motion.div 
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.5 }}
          className="lg:col-span-2 bg-white rounded-2xl border border-slate-200 p-6 shadow-sm"
        >
          <h2 className="text-base font-semibold text-slate-900 mb-6">Activity & Alerts Timeline</h2>
          <div className="h-80 w-full min-h-[320px]">
            <ResponsiveContainer width="100%" height="100%" minWidth={0} minHeight={0}>
              <AreaChart data={data} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
                <defs>
                  <linearGradient id="colorActive" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#4f46e5" stopOpacity={0.1}/>
                    <stop offset="95%" stopColor="#4f46e5" stopOpacity={0}/>
                  </linearGradient>
                  <linearGradient id="colorAlerts" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#e11d48" stopOpacity={0.1}/>
                    <stop offset="95%" stopColor="#e11d48" stopOpacity={0}/>
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0" />
                <XAxis dataKey="time" stroke="#64748b" fontSize={12} tickLine={false} axisLine={false} dy={10} />
                <YAxis yAxisId="left" stroke="#64748b" fontSize={12} tickLine={false} axisLine={false} dx={-10} />
                <YAxis yAxisId="right" orientation="right" stroke="#64748b" fontSize={12} tickLine={false} axisLine={false} dx={10} />
                <Tooltip 
                  contentStyle={{ backgroundColor: '#ffffff', borderRadius: '12px', border: '1px solid #e2e8f0', boxShadow: '0 4px 6px -1px rgba(0,0,0,0.1)' }}
                />
                <Area yAxisId="left" type="monotone" dataKey="active" stroke="#4f46e5" strokeWidth={3} fillOpacity={1} fill="url(#colorActive)" name="Active Students" />
                <Area yAxisId="right" type="monotone" dataKey="alerts" stroke="#e11d48" strokeWidth={3} fillOpacity={1} fill="url(#colorAlerts)" name="Alerts" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </motion.div>

        <motion.div 
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.6 }}
          className="bg-white rounded-2xl border border-slate-200 p-6 shadow-sm flex flex-col"
        >
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-base font-semibold text-slate-900">Recent Alerts</h2>
            <button className="text-sm font-medium text-indigo-600 hover:text-indigo-700">View All</button>
          </div>
          <div className="flex-1 overflow-y-auto pr-2 space-y-3">
            {combinedAlerts.map((alert, idx) => (
              <motion.div 
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: 0.7 + (idx * 0.1) }}
                key={alert.id} 
                onClick={() => navigate(`/student/${alert.studentId}`)}
                className="flex items-start gap-3 p-3 rounded-xl border border-slate-100 bg-slate-50/50 hover:bg-slate-50 hover:border-slate-200 transition-colors cursor-pointer"
              >
                <div className={`mt-0.5 p-2 rounded-lg ${
                  alert.severity === 'high' ? 'bg-rose-100 text-rose-600' :
                  alert.severity === 'medium' ? 'bg-amber-100 text-amber-600' :
                  'bg-blue-100 text-blue-600'
                }`}>
                  <AlertTriangle className="w-4 h-4" />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-slate-900 truncate">{alert.student}</p>
                  <p className="text-xs text-slate-500 truncate mt-0.5">{alert.type}</p>
                </div>
                <span className="text-xs text-slate-400 whitespace-nowrap">{alert.time}</span>
              </motion.div>
            ))}
          </div>
        </motion.div>
      </div>

      {/* New Session Modal */}
      <AnimatePresence>
        {isNewSessionModalOpen && (
          <div className="fixed inset-0 bg-slate-900/50 backdrop-blur-sm flex items-center justify-center z-50 p-4">
            <motion.div
              initial={{ opacity: 0, scale: 0.95, y: 10 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.95, y: 10 }}
              className="bg-white rounded-2xl shadow-xl w-full max-w-md overflow-hidden"
            >
              <div className="flex items-center justify-between p-6 border-b border-slate-100 bg-slate-50/50">
                <h2 className="text-lg font-semibold text-slate-900">Create New Session</h2>
                <button 
                  onClick={() => setIsNewSessionModalOpen(false)}
                  className="p-2 text-slate-400 hover:text-slate-600 hover:bg-slate-100 rounded-xl transition-colors"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>
              
              <form onSubmit={handleCreateSession} className="p-6 space-y-6">
                <div className="space-y-2">
                  <label className="text-sm font-medium text-slate-700">Session Name</label>
                  <input 
                    type="text" 
                    required
                    value={sessionName}
                    onChange={(e) => setSessionName(e.target.value)}
                    className="w-full px-4 py-2.5 rounded-xl border border-slate-200 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-all bg-white text-slate-900 placeholder:text-slate-400" 
                    placeholder="e.g. CS101 Midterm Exam" 
                  />
                </div>

                <div className="space-y-2">
                  <label className="text-sm font-medium text-slate-700">Expected Student Count</label>
                  <input 
                    type="number" 
                    required
                    min="1"
                    value={studentCount}
                    onChange={(e) => setStudentCount(e.target.value)}
                    className="w-full px-4 py-2.5 rounded-xl border border-slate-200 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-all bg-white text-slate-900 placeholder:text-slate-400" 
                    placeholder="e.g. 50" 
                  />
                </div>

                <div className="space-y-2">
                  <label className="text-sm font-medium text-slate-700">Generated Exam Code</label>
                  <div className="flex items-center gap-2">
                    <div className="relative flex-1">
                      <input 
                        type="text" 
                        readOnly
                        value={examCode}
                        className="w-full pl-4 pr-10 py-2.5 rounded-xl border border-slate-200 text-sm font-mono font-medium focus:outline-none bg-slate-50 text-slate-900" 
                      />
                      <button 
                        type="button"
                        onClick={handleCopyCode}
                        className="absolute right-2 top-1/2 -translate-y-1/2 p-1.5 text-slate-400 hover:text-indigo-600 hover:bg-indigo-50 rounded-lg transition-colors"
                        title="Copy Code"
                      >
                        <Copy className="w-4 h-4" />
                      </button>
                    </div>
                    <button 
                      type="button"
                      onClick={generateExamCode}
                      className="p-2.5 border border-slate-200 text-slate-500 hover:text-indigo-600 hover:border-indigo-200 hover:bg-indigo-50 rounded-xl transition-colors"
                      title="Regenerate Code"
                    >
                      <RefreshCw className="w-4 h-4" />
                    </button>
                  </div>
                  <p className="text-xs text-rose-500 mt-1 font-semibold underline">CRITICAL: Share this code with students. They cannot join without it.</p>
                </div>

                <div className="pt-4 flex items-center justify-end gap-3 border-t border-slate-100">
                  <button 
                    type="button" 
                    onClick={() => setIsNewSessionModalOpen(false)}
                    className="px-4 py-2.5 rounded-xl text-sm font-medium text-slate-600 hover:bg-slate-100 hover:text-slate-900 transition-colors"
                  >
                    Cancel
                  </button>
                  <button 
                    type="submit" 
                    disabled={isCreating}
                    className="px-5 py-2.5 rounded-xl text-sm font-semibold text-white bg-indigo-600 hover:bg-indigo-700 transition-colors shadow-sm active:scale-95 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center min-w-[120px]"
                  >
                    {isCreating ? (
                      <>
                        <RefreshCw className="w-4 h-4 mr-2 animate-spin" />
                        Creating...
                      </>
                    ) : (
                      "Create Session"
                    )}
                  </button>
                </div>
              </form>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </div>
  );
}
