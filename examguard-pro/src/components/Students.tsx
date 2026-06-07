import { Search, ShieldAlert, CheckCircle2, UserX, ArrowUpDown, ArrowUp, ArrowDown, ChevronRight } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { motion } from "motion/react";
import { config } from "../config";

type SortKey = "name" | "latestExamId" | "latestStatus" | "latestRiskScore" | "latestSeenAt" | "sessionCount";

interface StudentAttendee {
  studentId: string;
  name: string;
  latestExamId: string;
  latestStatus: string;
  latestRiskLevel: string;
  latestRiskScore: number;
  latestEffortScore: number;
  latestSeenAt: string;
  sessionCount: number;
  activeSessionCount: number;
  flaggedSessionCount: number;
  avgRisk: number;
  avgEffort: number;
}

const ACTIVE_STATUSES = new Set(["active", "recording"]);
const FLAGGED_STATUSES = new Set(["review", "suspicious"]);

export function Students() {
  const navigate = useNavigate();
  const [students, setStudents] = useState<StudentAttendee[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [sortKey, setSortKey] = useState<SortKey>('latestSeenAt');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc');
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<'all' | 'active' | 'flagged' | 'ended'>('all');

  useEffect(() => {
    const fetchAttendees = async () => {
      setIsLoading(true);
      try {
        const response = await fetch(`${config.apiUrl}/sessions?active_only=false&limit=500`);
        if (!response.ok) {
          throw new Error(`Failed to fetch sessions (${response.status})`);
        }

        const sessionRows = await response.json();
        const studentRows = sessionRows.filter((session: any) => session?.student_id && !session.student_id.startsWith('PROCTOR-'));
        const grouped = new Map<string, any[]>();

        for (const session of studentRows) {
          const key = session.student_id;
          if (!grouped.has(key)) {
            grouped.set(key, []);
          }
          grouped.get(key)!.push(session);
        }

        const derivedStudents: StudentAttendee[] = Array.from(grouped.entries()).map(([studentId, sessions]) => {
          const sortedSessions = [...sessions].sort((a, b) => new Date(b.started_at).getTime() - new Date(a.started_at).getTime());
          const latest = sortedSessions[0];
          const avgRisk = sessions.length > 0
            ? Math.round(sessions.reduce((acc, session) => acc + Number(session.risk_score || 0), 0) / sessions.length)
            : 0;
          const avgEffort = sessions.length > 0
            ? Math.round(sessions.reduce((acc, session) => acc + Number(session.engagement_score || session.effort_alignment || 0), 0) / sessions.length)
            : 0;

          return {
            studentId,
            name: latest.student_name || studentId,
            latestExamId: latest.exam_id || 'Unknown',
            latestStatus: latest.status || 'ended',
            latestRiskLevel: latest.risk_level || 'safe',
            latestRiskScore: Number(latest.risk_score || 0),
            latestEffortScore: Number(latest.engagement_score || latest.effort_alignment || 0),
            latestSeenAt: latest.started_at || new Date().toISOString(),
            sessionCount: sessions.length,
            activeSessionCount: sessions.filter((session) => ACTIVE_STATUSES.has(String(session.status || '').toLowerCase())).length,
            flaggedSessionCount: sessions.filter((session) => FLAGGED_STATUSES.has(String(session.risk_level || '').toLowerCase())).length,
            avgRisk,
            avgEffort,
          };
        });

        setStudents(derivedStudents);
      } catch (error) {
        console.error('Failed to load student attendees:', error);
        setStudents([]);
      } finally {
        setIsLoading(false);
      }
    };

    fetchAttendees();
  }, []);

  const sortedStudents = useMemo(() => {
    return [...students]
      .filter((student) => {
        const matchesSearch = student.name.toLowerCase().includes(searchQuery.toLowerCase()) || student.studentId.toLowerCase().includes(searchQuery.toLowerCase()) || student.latestExamId.toLowerCase().includes(searchQuery.toLowerCase());
        if (!matchesSearch) return false;

        if (statusFilter === 'active') {
          return student.activeSessionCount > 0;
        }
        if (statusFilter === 'flagged') {
          return student.flaggedSessionCount > 0 || student.latestRiskLevel === 'review' || student.latestRiskLevel === 'suspicious';
        }
        if (statusFilter === 'ended') {
          return student.activeSessionCount === 0;
        }
        return true;
      })
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
  }, [sortKey, sortOrder, searchQuery, statusFilter, students]);

  const totalStudents = students.length;
  const activeStudents = students.filter((student) => student.activeSessionCount > 0).length;
  const flaggedStudents = students.filter((student) => student.flaggedSessionCount > 0).length;
  const averageRisk = students.length > 0 ? Math.round(students.reduce((acc, student) => acc + student.avgRisk, 0) / students.length) : 0;

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
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Students in Session</h1>
          <p className="text-slate-500 mt-1 text-sm">Live attendees grouped by student, with attendance and risk history.</p>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-400">Students</p>
          <p className="mt-1 text-3xl font-bold text-slate-900">{totalStudents}</p>
        </div>
        <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-400">Active now</p>
          <p className="mt-1 text-3xl font-bold text-emerald-600">{activeStudents}</p>
        </div>
        <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-400">Flagged</p>
          <p className="mt-1 text-3xl font-bold text-rose-600">{flaggedStudents}</p>
        </div>
        <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-400">Avg risk</p>
          <p className="mt-1 text-3xl font-bold text-slate-900">{averageRisk}</p>
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
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value as typeof statusFilter)}
              className="px-3.5 py-2 rounded-xl border border-slate-200 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 bg-white cursor-pointer text-slate-700"
            >
              <option value="all">All Students</option>
              <option value="active">Active Now</option>
              <option value="flagged">Flagged</option>
              <option value="ended">Ended</option>
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
                <th className="px-6 py-4 font-semibold text-xs uppercase tracking-wider cursor-pointer hover:bg-slate-100 transition-colors" onClick={() => handleSort('latestExamId')}>
                  <div className="flex items-center">Latest Exam <SortIcon columnKey="latestExamId" /></div>
                </th>
                <th className="px-6 py-4 font-semibold text-xs uppercase tracking-wider cursor-pointer hover:bg-slate-100 transition-colors" onClick={() => handleSort('latestStatus')}>
                  <div className="flex items-center">Status <SortIcon columnKey="latestStatus" /></div>
                </th>
                <th className="px-6 py-4 font-semibold text-xs uppercase tracking-wider cursor-pointer hover:bg-slate-100 transition-colors" onClick={() => handleSort('latestRiskScore')}>
                  <div className="flex items-center">Risk Score <SortIcon columnKey="latestRiskScore" /></div>
                </th>
                <th className="px-6 py-4 font-semibold text-xs uppercase tracking-wider cursor-pointer hover:bg-slate-100 transition-colors" onClick={() => handleSort('sessionCount')}>
                  <div className="flex items-center">Sessions <SortIcon columnKey="sessionCount" /></div>
                </th>
                <th className="px-6 py-4 font-semibold text-xs uppercase tracking-wider cursor-pointer hover:bg-slate-100 transition-colors" onClick={() => handleSort('latestSeenAt')}>
                  <div className="flex items-center">Last Seen <SortIcon columnKey="latestSeenAt" /></div>
                </th>
                <th className="px-6 py-4 font-semibold text-xs uppercase tracking-wider text-right">Report</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {sortedStudents.map((student, idx) => (
                <motion.tr 
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: idx * 0.05 }}
                  key={student.studentId} 
                  onClick={() => navigate(`/student/${student.studentId}`)}
                  className="hover:bg-slate-50/80 transition-colors group cursor-pointer"
                >
                  <td className="px-6 py-4">
                    <div className="flex items-center gap-3.5">
                      <div className="w-10 h-10 rounded-full bg-indigo-100 text-indigo-700 flex items-center justify-center font-bold text-sm border border-indigo-200 shadow-sm">
                        {student.name.split(' ').map(n => n[0]).join('').slice(0, 2).toUpperCase()}
                      </div>
                      <div>
                        <p className="font-medium text-slate-900">{student.name}</p>
                        <p className="text-xs text-slate-500 mt-0.5">{student.studentId}</p>
                      </div>
                    </div>
                  </td>
                  <td className="px-6 py-4 text-slate-600 font-medium">{student.latestExamId}</td>
                  <td className="px-6 py-4">
                    <div className="flex items-center gap-2">
                      {student.activeSessionCount > 0 && <CheckCircle2 className="w-4 h-4 text-emerald-500" />}
                      {student.activeSessionCount === 0 && student.latestRiskLevel === 'safe' && <UserX className="w-4 h-4 text-slate-400" />}
                      {student.flaggedSessionCount > 0 && <ShieldAlert className="w-4 h-4 text-rose-500" />}
                      <span className={`text-[13px] font-medium capitalize ${
                        student.activeSessionCount > 0 ? 'text-emerald-600' :
                        student.flaggedSessionCount > 0 ? 'text-rose-600' :
                        'text-slate-500'
                      }`}>
                        {student.activeSessionCount > 0 ? 'active' : student.flaggedSessionCount > 0 ? 'flagged' : 'ended'}
                      </span>
                    </div>
                  </td>
                  <td className="px-6 py-4">
                    <div className="flex items-center gap-3">
                      <div className="w-20 h-1.5 bg-slate-100 rounded-full overflow-hidden">
                        <div 
                          className={`h-full rounded-full ${
                            student.latestRiskScore > 75 ? 'bg-rose-500' :
                            student.latestRiskScore > 30 ? 'bg-amber-500' :
                            'bg-emerald-500'
                          }`}
                          style={{ width: `${student.latestRiskScore}%` }}
                        />
                      </div>
                      <span className={`text-[11px] font-semibold ${
                        student.latestRiskScore > 75 ? 'text-rose-600' :
                        student.latestRiskScore > 30 ? 'text-amber-600' :
                        'text-emerald-600'
                      }`}>
                        {student.latestRiskScore}/100
                      </span>
                    </div>
                  </td>
                  <td className="px-6 py-4 text-slate-500 text-sm">{student.sessionCount}</td>
                  <td className="px-6 py-4 text-slate-500 text-sm">{new Date(student.latestSeenAt).toLocaleString()}</td>
                  <td className="px-6 py-4 text-right">
                    <button
                      onClick={(event) => {
                        event.stopPropagation();
                        navigate(`/student/${student.studentId}`);
                      }}
                      className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 px-3 py-1.5 text-sm font-medium text-slate-700 hover:bg-slate-50 hover:border-indigo-200 hover:text-indigo-600 transition-colors bg-white shadow-sm active:scale-95 opacity-0 group-hover:opacity-100 focus:opacity-100"
                    >
                      View Report
                      <ChevronRight className="w-4 h-4" />
                    </button>
                  </td>
                </motion.tr>
              ))}
              {sortedStudents.length === 0 && (
                <tr>
                  <td colSpan={6} className="px-6 py-12 text-center text-slate-500">
                    {isLoading ? 'Loading student sessions...' : 'No students found matching your search.'}
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
