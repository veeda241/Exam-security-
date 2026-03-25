import React, { useState, useMemo } from "react";
import { AlertTriangle, Search, Filter, Eye, Check, X, Camera, Layout, ShieldAlert } from "lucide-react";
import { motion, AnimatePresence } from "motion/react";

const initialAlerts: any[] = [];

export function Alerts() {
  const [alerts, setAlerts] = useState(initialAlerts);
  const [searchQuery, setSearchQuery] = useState('');
  const [filterStatus, setFilterStatus] = useState('All');
  const [selectedAlert, setSelectedAlert] = useState<any>(null);

  const handleResolve = (id: number, e?: React.MouseEvent) => {
    if (e) e.stopPropagation();
    setAlerts(alerts.map(a => a.id === id ? { ...a, status: 'resolved' } : a));
  };

  const filteredAlerts = useMemo(() => {
    return alerts.filter(alert => {
      const matchesSearch = 
        alert.student.toLowerCase().includes(searchQuery.toLowerCase()) ||
        alert.type.toLowerCase().includes(searchQuery.toLowerCase()) ||
        alert.session.toLowerCase().includes(searchQuery.toLowerCase());
      
      const matchesStatus = filterStatus === 'All' || 
        (filterStatus === 'Unresolved' && alert.status === 'unresolved') ||
        (filterStatus === 'Resolved' && alert.status === 'resolved');

      return matchesSearch && matchesStatus;
    });
  }, [alerts, searchQuery, filterStatus]);

  const unresolvedCount = alerts.filter(a => a.status === 'unresolved').length;
  const highSeverityCount = alerts.filter(a => a.severity === 'high' && a.status === 'unresolved').length;

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-20 md:pb-0">
      {/* Header & Stats */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Security Alerts</h1>
          <p className="text-slate-500 mt-1 text-sm">Review and manage AI-detected anomalies.</p>
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

      {/* Main Content */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
        {/* Toolbar */}
        <div className="p-5 border-b border-slate-200 flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-slate-50/50">
          <div className="relative w-full sm:max-w-md">
            <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
            <input 
              type="text" 
              placeholder="Search alerts by student, type, or session..." 
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-10 pr-4 py-2 rounded-xl border border-slate-200 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-all bg-white text-slate-900 placeholder:text-slate-400"
            />
          </div>
          <div className="flex items-center gap-3">
            <select 
              value={filterStatus}
              onChange={(e) => setFilterStatus(e.target.value)}
              className="px-3.5 py-2 rounded-xl border border-slate-200 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 bg-white cursor-pointer text-slate-700 font-medium"
            >
              <option value="All">All Status</option>
              <option value="Unresolved">Unresolved</option>
              <option value="Resolved">Resolved</option>
            </select>
          </div>
        </div>

        {/* Table */}
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="bg-slate-50 text-slate-500 border-b border-slate-200">
              <tr>
                <th className="px-6 py-4 font-semibold text-xs uppercase tracking-wider">Alert Type</th>
                <th className="px-6 py-4 font-semibold text-xs uppercase tracking-wider">Student</th>
                <th className="px-6 py-4 font-semibold text-xs uppercase tracking-wider">Session</th>
                <th className="px-6 py-4 font-semibold text-xs uppercase tracking-wider">Time</th>
                <th className="px-6 py-4 font-semibold text-xs uppercase tracking-wider">Status</th>
                <th className="px-6 py-4 font-semibold text-xs uppercase tracking-wider text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              <AnimatePresence>
                {filteredAlerts.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="px-6 py-12 text-center text-slate-500">
                      <ShieldAlert className="w-12 h-12 mx-auto text-slate-300 mb-3" />
                      <p className="text-lg font-medium text-slate-900">No alerts found</p>
                      <p className="text-sm">Try adjusting your search or filters.</p>
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
                            alert.severity === 'high' ? 'bg-rose-50 text-rose-600 border-rose-100' :
                            alert.severity === 'medium' ? 'bg-amber-50 text-amber-600 border-amber-100' :
                            'bg-blue-50 text-blue-600 border-blue-100'
                          }`}>
                            <AlertTriangle className="w-4 h-4" />
                          </div>
                          <span className="font-medium text-slate-900">{alert.type}</span>
                        </div>
                      </td>
                      <td className="px-6 py-4 text-slate-600 font-medium">{alert.student}</td>
                      <td className="px-6 py-4 text-slate-600">{alert.session}</td>
                      <td className="px-6 py-4 text-slate-500 text-[13px]">{alert.time}</td>
                      <td className="px-6 py-4">
                        <span className={`inline-flex items-center px-2.5 py-1 rounded-md text-xs font-semibold border ${
                          alert.status === 'resolved' ? 'bg-emerald-50 text-emerald-700 border-emerald-200' :
                          'bg-rose-50 text-rose-700 border-rose-200'
                        }`}>
                          {alert.status.charAt(0).toUpperCase() + alert.status.slice(1)}
                        </span>
                      </td>
                      <td className="px-6 py-4 text-right">
                        <div className="flex items-center justify-end gap-2">
                          <button 
                            onClick={(e) => { e.stopPropagation(); setSelectedAlert(alert); }}
                            className="p-1.5 text-slate-400 hover:text-indigo-600 hover:bg-indigo-50 rounded-lg transition-colors opacity-0 group-hover:opacity-100 focus:opacity-100" 
                            title="View Evidence"
                          >
                            <Eye className="w-4 h-4" />
                          </button>
                          {alert.status === 'unresolved' && (
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

      {/* Evidence Modal */}
      <AnimatePresence>
        {selectedAlert && (
          <div className="fixed inset-0 bg-slate-900/50 backdrop-blur-sm flex items-center justify-center z-50 p-4">
            <motion.div
              initial={{ opacity: 0, scale: 0.95, y: 10 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.95, y: 10 }}
              className="bg-white p-0 rounded-2xl w-[800px] max-w-full shadow-xl flex flex-col overflow-hidden max-h-[90vh]"
            >
              {/* Header */}
              <div className="flex items-center justify-between p-6 border-b border-slate-100 bg-slate-50/50 shrink-0">
                <div className="flex items-center gap-4">
                  <div className={`p-3 rounded-xl border shadow-sm ${
                    selectedAlert.severity === 'high' ? 'bg-rose-50 text-rose-600 border-rose-100' :
                    selectedAlert.severity === 'medium' ? 'bg-amber-50 text-amber-600 border-amber-100' :
                    'bg-blue-50 text-blue-600 border-blue-100'
                  }`}>
                    <AlertTriangle className="w-6 h-6" />
                  </div>
                  <div>
                    <h2 className="text-xl font-bold text-slate-900 tracking-tight">{selectedAlert.type}</h2>
                    <p className="text-sm text-slate-500">
                      {selectedAlert.student} • {selectedAlert.session} • {selectedAlert.time}
                    </p>
                  </div>
                </div>
                <button onClick={() => setSelectedAlert(null)} className="p-2 text-slate-400 hover:text-slate-600 hover:bg-slate-100 rounded-xl transition-colors">
                  <X className="w-5 h-5" />
                </button>
              </div>

              {/* Content */}
              <div className="p-6 overflow-y-auto space-y-6">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  {/* Camera Evidence */}
                  <div className="space-y-3">
                    <h3 className="text-sm font-semibold text-slate-900 flex items-center gap-2">
                      <Camera className="w-4 h-4 text-slate-500" />
                      Camera Capture at Time of Alert
                    </h3>
                    <div className="bg-slate-100 rounded-xl border border-slate-200 overflow-hidden aspect-video relative shadow-sm">
                      <img 
                        src={`https://picsum.photos/seed/${selectedAlert.id}-cam/600/400`} 
                        alt="Evidence camera" 
                        className="w-full h-full object-cover"
                        referrerPolicy="no-referrer"
                      />
                      <div className="absolute top-2 left-2 bg-rose-500 text-white text-[10px] font-bold px-2 py-1 rounded-md uppercase tracking-wider shadow-sm">
                        Evidence
                      </div>
                    </div>
                  </div>

                  {/* Screen Evidence */}
                  <div className="space-y-3">
                    <h3 className="text-sm font-semibold text-slate-900 flex items-center gap-2">
                      <Layout className="w-4 h-4 text-slate-500" />
                      Screen Capture at Time of Alert
                    </h3>
                    <div className="bg-slate-100 rounded-xl border border-slate-200 overflow-hidden aspect-video relative shadow-sm">
                      <img 
                        src={`https://picsum.photos/seed/${selectedAlert.id}-screen/600/400`} 
                        alt="Evidence screen" 
                        className="w-full h-full object-cover"
                        referrerPolicy="no-referrer"
                      />
                      <div className="absolute top-2 left-2 bg-rose-500 text-white text-[10px] font-bold px-2 py-1 rounded-md uppercase tracking-wider shadow-sm">
                        Evidence
                      </div>
                    </div>
                  </div>
                </div>

                {/* Details */}
                <div className="bg-slate-50 rounded-xl p-4 border border-slate-100">
                  <h3 className="text-sm font-semibold text-slate-900 mb-2">AI Analysis Details</h3>
                  <p className="text-sm text-slate-700">
                    The AI proctoring model detected <span className="font-semibold">{selectedAlert.type.toLowerCase()}</span> with a confidence score of {selectedAlert.riskScore}%. 
                    This behavior deviates from the established baseline for this student. Please review the captured evidence to determine if academic dishonesty occurred.
                  </p>
                </div>
              </div>

              {/* Footer */}
              <div className="p-6 border-t border-slate-100 bg-slate-50/50 flex items-center justify-between shrink-0">
                <button onClick={() => setSelectedAlert(null)} className="px-5 py-2.5 bg-white border border-slate-200 text-slate-700 font-medium rounded-xl hover:bg-slate-50 transition-colors shadow-sm active:scale-95">
                  Close
                </button>
                {selectedAlert.status === 'unresolved' ? (
                  <button 
                    onClick={() => {
                      handleResolve(selectedAlert.id);
                      setSelectedAlert(null);
                    }}
                    className="inline-flex items-center justify-center px-5 py-2.5 bg-emerald-600 text-white font-semibold rounded-xl hover:bg-emerald-700 transition-all shadow-sm active:scale-95"
                  >
                    <Check className="w-4 h-4 mr-2" />
                    Acknowledge & Resolve
                  </button>
                ) : (
                  <div className="inline-flex items-center justify-center px-5 py-2.5 bg-emerald-50 text-emerald-700 font-semibold rounded-xl border border-emerald-200">
                    <Check className="w-4 h-4 mr-2" />
                    Resolved
                  </div>
                )}
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </div>
  );
}
