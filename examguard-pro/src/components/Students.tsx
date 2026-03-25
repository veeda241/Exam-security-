import { Search, Plus, MoreVertical, ShieldAlert, CheckCircle2, UserX, ArrowUpDown, ArrowUp, ArrowDown } from "lucide-react";
import { useState, useMemo } from "react";
import { motion } from "motion/react";
import { StudentModal } from "./StudentModal";

const initialStudents: any[] = [];

type SortKey = keyof typeof initialStudents[0];

export function Students() {
  const [sortKey, setSortKey] = useState<SortKey>('name');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('asc');
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedStudent, setSelectedStudent] = useState<any>(null);

  const sortedStudents = useMemo(() => {
    return [...initialStudents]
      .filter(s => s.name.toLowerCase().includes(searchQuery.toLowerCase()) || s.id.toLowerCase().includes(searchQuery.toLowerCase()))
      .sort((a, b) => {
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
  }, [sortKey, sortOrder, searchQuery]);

  const handleSort = (key: SortKey) => {
    if (sortKey === key) {
      setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc');
    } else {
      setSortKey(key);
      setSortOrder('asc');
    }
  };

  const SortIcon = ({ columnKey }: { columnKey: SortKey }) => {
    if (sortKey !== columnKey) return <ArrowUpDown className="w-3.5 h-3.5 ml-1.5 opacity-40" />;
    return sortOrder === 'asc' ? <ArrowUp className="w-3.5 h-3.5 ml-1.5 text-indigo-600" /> : <ArrowDown className="w-3.5 h-3.5 ml-1.5 text-indigo-600" />;
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Students Directory</h1>
          <p className="text-slate-500 mt-1 text-sm">Monitor enrolled students and their risk profiles.</p>
        </div>
      </div>

      <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
        <div className="p-5 border-b border-slate-200 flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-slate-50/50">
          <div className="relative w-full sm:max-w-md">
            <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
            <input 
              type="text" 
              placeholder="Search by name or ID..." 
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-10 pr-4 py-2 rounded-xl border border-slate-200 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-all bg-white text-slate-900 placeholder:text-slate-400"
            />
          </div>
          <div className="flex items-center gap-3">
            <select className="px-3.5 py-2 rounded-xl border border-slate-200 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 bg-white cursor-pointer text-slate-700">
              <option>All Courses</option>
              <option>Computer Science</option>
              <option>Mathematics</option>
              <option>Physics</option>
            </select>
            <select className="px-3.5 py-2 rounded-xl border border-slate-200 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 bg-white cursor-pointer text-slate-700">
              <option>All Status</option>
              <option>Active</option>
              <option>Flagged</option>
              <option>Offline</option>
            </select>
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="bg-slate-50 text-slate-500 border-b border-slate-200">
              <tr>
                <th className="px-6 py-4 font-semibold text-xs uppercase tracking-wider cursor-pointer hover:bg-slate-100 transition-colors" onClick={() => handleSort('name')}>
                  <div className="flex items-center">Student <SortIcon columnKey="name" /></div>
                </th>
                <th className="px-6 py-4 font-semibold text-xs uppercase tracking-wider cursor-pointer hover:bg-slate-100 transition-colors" onClick={() => handleSort('course')}>
                  <div className="flex items-center">Course <SortIcon columnKey="course" /></div>
                </th>
                <th className="px-6 py-4 font-semibold text-xs uppercase tracking-wider cursor-pointer hover:bg-slate-100 transition-colors" onClick={() => handleSort('status')}>
                  <div className="flex items-center">Status <SortIcon columnKey="status" /></div>
                </th>
                <th className="px-6 py-4 font-semibold text-xs uppercase tracking-wider cursor-pointer hover:bg-slate-100 transition-colors" onClick={() => handleSort('riskScore')}>
                  <div className="flex items-center">Risk Score <SortIcon columnKey="riskScore" /></div>
                </th>
                <th className="px-6 py-4 font-semibold text-xs uppercase tracking-wider cursor-pointer hover:bg-slate-100 transition-colors" onClick={() => handleSort('lastActive')}>
                  <div className="flex items-center">Last Active <SortIcon columnKey="lastActive" /></div>
                </th>
                <th className="px-6 py-4 font-semibold text-xs uppercase tracking-wider text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {sortedStudents.map((student, idx) => (
                <motion.tr 
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: idx * 0.05 }}
                  key={student.id} 
                  onClick={() => setSelectedStudent(student)}
                  className="hover:bg-slate-50/80 transition-colors group cursor-pointer"
                >
                  <td className="px-6 py-4">
                    <div className="flex items-center gap-3.5">
                      <div className="w-10 h-10 rounded-full bg-indigo-100 text-indigo-700 flex items-center justify-center font-bold text-sm border border-indigo-200 shadow-sm">
                        {student.name.split(' ').map(n => n[0]).join('')}
                      </div>
                      <div>
                        <p className="font-medium text-slate-900">{student.name}</p>
                        <p className="text-xs text-slate-500 mt-0.5">{student.email}</p>
                      </div>
                    </div>
                  </td>
                  <td className="px-6 py-4 text-slate-600 font-medium">{student.course}</td>
                  <td className="px-6 py-4">
                    <div className="flex items-center gap-2">
                      {student.status === 'active' && <CheckCircle2 className="w-4 h-4 text-emerald-500" />}
                      {student.status === 'flagged' && <ShieldAlert className="w-4 h-4 text-rose-500" />}
                      {student.status === 'offline' && <UserX className="w-4 h-4 text-slate-400" />}
                      <span className={`text-[13px] font-medium capitalize ${
                        student.status === 'active' ? 'text-emerald-600' :
                        student.status === 'flagged' ? 'text-rose-600' :
                        'text-slate-500'
                      }`}>
                        {student.status}
                      </span>
                    </div>
                  </td>
                  <td className="px-6 py-4">
                    <div className="flex items-center gap-3">
                      <div className="w-20 h-1.5 bg-slate-100 rounded-full overflow-hidden">
                        <div 
                          className={`h-full rounded-full ${
                            student.riskScore > 75 ? 'bg-rose-500' :
                            student.riskScore > 30 ? 'bg-amber-500' :
                            'bg-emerald-500'
                          }`}
                          style={{ width: `${student.riskScore}%` }}
                        />
                      </div>
                      <span className={`text-[11px] font-semibold ${
                        student.riskScore > 75 ? 'text-rose-600' :
                        student.riskScore > 30 ? 'text-amber-600' :
                        'text-emerald-600'
                      }`}>
                        {student.riskScore}/100
                      </span>
                    </div>
                  </td>
                  <td className="px-6 py-4 text-slate-500 text-sm">{student.lastActive}</td>
                  <td className="px-6 py-4 text-right">
                    <button className="p-1.5 text-slate-400 hover:text-indigo-600 hover:bg-indigo-50 rounded-lg transition-colors opacity-0 group-hover:opacity-100 focus:opacity-100">
                      <MoreVertical className="w-4 h-4" />
                    </button>
                  </td>
                </motion.tr>
              ))}
              {sortedStudents.length === 0 && (
                <tr>
                  <td colSpan={6} className="px-6 py-12 text-center text-slate-500">
                    No students found matching your search.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      <StudentModal 
        isOpen={!!selectedStudent} 
        student={selectedStudent} 
        onClose={() => setSelectedStudent(null)} 
      />
    </div>
  );
}
