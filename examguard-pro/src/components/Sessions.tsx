import { Search, MoreVertical, Play, Square, Video, ArrowUpDown, ArrowUp, ArrowDown } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { motion } from "motion/react";
import React, { useState, useMemo, useEffect } from "react";
import { config } from '../config';

export function Sessions() {
  const navigate = useNavigate();
  const [sessions, setSessions] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [sortKey, setSortKey] = useState<string>('name');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('asc');
  
  useEffect(() => {
    const fetchSessions = async () => {
      try {
        const response = await fetch(`${config.apiUrl}/sessions/`);
        if (response.ok) {
          const data = await response.json();
          setSessions(data);
        }
      } catch (error) {
        console.error("Failed to fetch sessions:", error);
      } finally {
        setIsLoading(false);
      }
    };
    fetchSessions();
  }, []);

  const sortedSessions = useMemo(() => {
    return [...sessions].sort((a, b) => {
      let aValue = a[sortKey];
      let bValue = b[sortKey];

      if (typeof aValue === 'string') {
        aValue = aValue.toLowerCase();
        bValue = (bValue as string).toLowerCase();
      }

      if (aValue < bValue) return sortOrder === 'asc' ? -1 : 1;
      if (aValue > bValue) return sortOrder === 'asc' ? 1 : -1;
      return 0;
    });
  }, [sessions, sortKey, sortOrder]);

  const handleSort = (key: string) => {
    if (sortKey === key) {
      setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc');
    } else {
      setSortKey(key);
      setSortOrder('asc');
    }
  };

  const SortIcon = ({ columnKey }: { columnKey: string }) => {
    if (sortKey !== columnKey) return <ArrowUpDown className="w-3.5 h-3.5 ml-1.5 opacity-40" />;
    return sortOrder === 'asc' ? <ArrowUp className="w-3.5 h-3.5 ml-1.5 text-indigo-600" /> : <ArrowDown className="w-3.5 h-3.5 ml-1.5 text-indigo-600" />;
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Exam Sessions</h1>
          <p className="text-slate-500 mt-1">Manage and monitor active exam sessions.</p>
        </div>
        <div className="flex items-center gap-3">
          <button 
            onClick={async () => {
              if (confirm("Are you sure you want to clear ALL session data? This cannot be undone.")) {
                try {
                  const res = await fetch(`${config.apiUrl}/sessions/clear`, { method: 'DELETE' });
                  if (res.ok) {
                    setSessions([]);
                  }
                } catch (e) {
                  alert("Failed to clear sessions");
                }
              }
            }}
            className="inline-flex items-center justify-center rounded-xl bg-white border border-rose-200 px-4 py-2.5 text-sm font-semibold text-rose-600 hover:bg-rose-50 transition-colors shadow-sm active:scale-95"
          >
            Clear All Sessions
          </button>
        </div>
      </div>

      <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
        <div className="p-5 border-b border-slate-200 flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-slate-50/50">
          <div className="relative w-full sm:max-w-md">
            <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
            <input 
              type="text" 
              placeholder="Search sessions..." 
              className="w-full pl-10 pr-4 py-2 rounded-xl border border-slate-200 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-all bg-white text-slate-900 placeholder:text-slate-400"
            />
          </div>
        </div>

        {isLoading ? (
          <div className="p-12 text-center text-slate-500">Loading sessions...</div>
        ) : sessions.length === 0 ? (
          <div className="p-12 text-center text-slate-500">No active sessions found.</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="bg-slate-50 text-slate-500 border-b border-slate-200">
                <tr>
                  <th className="px-6 py-4 font-semibold text-xs uppercase tracking-wider cursor-pointer hover:bg-slate-100 transition-colors" onClick={() => handleSort('student_name')}>
                    <div className="flex items-center">Student Name <SortIcon columnKey="student_name" /></div>
                  </th>
                  <th className="px-6 py-4 font-semibold text-xs uppercase tracking-wider cursor-pointer hover:bg-slate-100 transition-colors" onClick={() => handleSort('exam_id')}>
                    <div className="flex items-center">Exam ID <SortIcon columnKey="exam_id" /></div>
                  </th>
                  <th className="px-6 py-4 font-semibold text-xs uppercase tracking-wider cursor-pointer hover:bg-slate-100 transition-colors" onClick={() => handleSort('status')}>
                    <div className="flex items-center">Status <SortIcon columnKey="status" /></div>
                  </th>
                  <th className="px-6 py-4 font-semibold text-xs uppercase tracking-wider cursor-pointer hover:bg-slate-100 transition-colors" onClick={() => handleSort('risk_level')}>
                    <div className="flex items-center">Risk <SortIcon columnKey="risk_level" /></div>
                  </th>
                  <th className="px-6 py-4 font-semibold text-xs uppercase tracking-wider text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {sortedSessions.map((session, idx) => (
                  <motion.tr 
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: idx * 0.05 }}
                    key={session.id} 
                    onClick={() => navigate(`/sessions/${session.id}`)}
                    className="hover:bg-slate-50/80 transition-colors cursor-pointer group"
                  >
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-3.5">
                        <div className={`p-2 rounded-xl border shadow-sm ${
                          session.status === 'active' ? 'bg-emerald-50 border-emerald-100 text-emerald-600' : 'bg-slate-100 border-slate-200 text-slate-500'
                        }`}>
                          <Video className="w-4 h-4" />
                        </div>
                        <div>
                          <p className="font-medium text-slate-900">{session.student_name}</p>
                          <p className="text-xs text-slate-500 mt-0.5">{session.id}</p>
                        </div>
                      </div>
                    </td>
                    <td className="px-6 py-4 text-slate-600 font-medium">{session.exam_id}</td>
                    <td className="px-6 py-4">
                      <span className={`inline-flex items-center px-2.5 py-1 rounded-md text-xs font-semibold border ${
                        session.status === 'active' ? 'bg-emerald-50 text-emerald-700 border-emerald-200' : 'bg-slate-100 text-slate-700 border-slate-200'
                      }`}>
                        {session.status}
                      </span>
                    </td>
                    <td className="px-6 py-4">
                       <span className={`px-2 py-1 rounded text-xs font-bold ${
                         session.risk_level === 'high' ? 'bg-rose-100 text-rose-700' : 
                         session.risk_level === 'medium' ? 'bg-amber-100 text-amber-700' : 
                         'bg-emerald-100 text-emerald-700'
                       }`}>
                         {session.risk_level}
                       </span>
                    </td>
                    <td className="px-6 py-4 text-right">
                      <div className="flex items-center justify-end gap-2" onClick={(e) => e.stopPropagation()}>
                        <button className="p-1.5 text-slate-400 hover:text-indigo-600 hover:bg-indigo-50 rounded-lg transition-colors active:scale-95 opacity-0 group-hover:opacity-100 focus:opacity-100">
                          <MoreVertical className="w-4 h-4" />
                        </button>
                      </div>
                    </td>
                  </motion.tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
