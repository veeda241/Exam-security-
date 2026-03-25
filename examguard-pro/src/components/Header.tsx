import { Bell, Search, User, ChevronDown, LogOut, Settings, Shield, ShieldCheck, AlertTriangle, X } from "lucide-react";
import { useState } from "react";
import { useAuth } from "../context/AuthContext";
import { useWebSocket } from "../hooks/useWebSocket";
import { useNavigate } from "react-router-dom";

export function Header() {
  const { logout } = useAuth();
  const navigate = useNavigate();
  const [isProfileOpen, setIsProfileOpen] = useState(false);
  const [isNotifOpen, setIsNotifOpen] = useState(false);
  const { messages: liveAlerts } = useWebSocket('/dashboard');

  // Filter to only real alerts
  const alerts = liveAlerts.filter(m => {
    const t = m.event_type || m.type;
    const ignore = ['connection', 'heartbeat', 'risk_score_update', 'session_started', 'session_ended', 'student_joined', 'student_left'];
    return t && !ignore.includes(t);
  });

  const formatTime = (ts: string) => {
    try {
      const d = new Date(ts);
      return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    } catch {
      return '';
    }
  };

  const getAlertColor = (level: string) => {
    switch (level) {
      case 'critical':
      case 'emergency': return 'bg-rose-100 text-rose-600';
      case 'warning': return 'bg-amber-100 text-amber-600';
      default: return 'bg-blue-100 text-blue-600';
    }
  };

  return (
    <header className="h-16 bg-white/80 backdrop-blur-md border-b border-slate-200 flex items-center justify-between px-4 sm:px-8 sticky top-0 z-30">
      <div className="flex items-center flex-1 gap-4">
        {/* Mobile Logo */}
        <div className="md:hidden flex items-center gap-2 font-bold text-lg tracking-tight text-slate-900">
          <div className="bg-indigo-50 border border-indigo-100 p-1.5 rounded-lg shadow-sm">
            <ShieldCheck className="w-5 h-5 text-indigo-600" />
          </div>
          <span>Exam<span className="text-indigo-600">Guard</span></span>
        </div>

        <div className="relative w-full max-w-md hidden sm:flex items-center bg-slate-50 border border-slate-200 rounded-xl px-3 py-2 focus-within:border-indigo-500 focus-within:ring-1 focus-within:ring-indigo-500 transition-all">
          <Search className="w-4 h-4 text-slate-400 mr-2" />
          <input 
            type="text" 
            placeholder="Search students, sessions, or alerts..." 
            className="bg-transparent border-none outline-none text-sm w-full placeholder:text-slate-400 text-slate-900" 
          />
          <div className="flex items-center gap-1 ml-2">
            <kbd className="px-1.5 py-0.5 text-[10px] font-medium text-slate-500 bg-white border border-slate-200 rounded-md shadow-sm">⌘</kbd>
            <kbd className="px-1.5 py-0.5 text-[10px] font-medium text-slate-500 bg-white border border-slate-200 rounded-md shadow-sm">K</kbd>
          </div>
        </div>
      </div>

      <div className="flex items-center gap-6">
        <div className="hidden md:flex items-center gap-2 px-3 py-1.5 bg-emerald-50 border border-emerald-100 rounded-full text-emerald-700 text-xs font-medium">
          <Shield className="w-3.5 h-3.5" />
          <span>System Secure</span>
        </div>

        {/* Notification Bell */}
        <div className="relative">
          <button
            onClick={() => { setIsNotifOpen(!isNotifOpen); setIsProfileOpen(false); }}
            className="relative p-2 text-slate-400 hover:text-slate-600 hover:bg-slate-50 rounded-full transition-colors"
          >
            <Bell className="w-5 h-5" />
            {alerts.length > 0 && (
              <span className="absolute top-1 right-1 min-w-[18px] h-[18px] flex items-center justify-center bg-rose-500 rounded-full border-2 border-white text-[10px] font-bold text-white">
                {alerts.length > 9 ? '9+' : alerts.length}
              </span>
            )}
          </button>

          {isNotifOpen && (
            <>
              <div className="fixed inset-0 z-40" onClick={() => setIsNotifOpen(false)}></div>
              <div className="absolute right-0 mt-2 w-80 bg-white rounded-2xl shadow-xl border border-slate-100 z-50 overflow-hidden">
                <div className="flex items-center justify-between px-4 py-3 border-b border-slate-100 bg-slate-50/50">
                  <h3 className="text-sm font-semibold text-slate-900">Notifications</h3>
                  <div className="flex items-center gap-2">
                    {alerts.length > 0 && (
                      <span className="text-xs font-medium text-indigo-600 bg-indigo-50 px-2 py-0.5 rounded-full">
                        {alerts.length} new
                      </span>
                    )}
                    <button
                      onClick={() => setIsNotifOpen(false)}
                      className="p-1 text-slate-400 hover:text-slate-600 rounded-lg hover:bg-slate-100 transition-colors"
                    >
                      <X className="w-4 h-4" />
                    </button>
                  </div>
                </div>

                <div className="max-h-80 overflow-y-auto">
                  {alerts.length === 0 ? (
                    <div className="flex flex-col items-center justify-center py-10 text-slate-400">
                      <Bell className="w-8 h-8 mb-2 opacity-30" />
                      <p className="text-sm">No notifications yet</p>
                      <p className="text-xs mt-1">Alerts will appear here during live exams</p>
                    </div>
                  ) : (
                    alerts.slice(0, 15).map((alert, idx) => (
                      <div
                        key={idx}
                        onClick={() => {
                          if (alert.session_id) navigate(`/sessions/${alert.session_id}`);
                          setIsNotifOpen(false);
                        }}
                        className="flex items-start gap-3 px-4 py-3 hover:bg-slate-50 transition-colors cursor-pointer border-b border-slate-50 last:border-b-0"
                      >
                        <div className={`mt-0.5 p-1.5 rounded-lg ${getAlertColor(alert.alert_level)}`}>
                          <AlertTriangle className="w-3.5 h-3.5" />
                        </div>
                        <div className="flex-1 min-w-0">
                          <p className="text-sm font-medium text-slate-900 truncate">
                            {(alert.event_type || '').replace(/_/g, ' ')}
                          </p>
                          <p className="text-xs text-slate-500 truncate mt-0.5">
                            {alert.data?.message || alert.student_id || 'System alert'}
                          </p>
                        </div>
                        <span className="text-[10px] text-slate-400 whitespace-nowrap mt-0.5">
                          {formatTime(alert.timestamp)}
                        </span>
                      </div>
                    ))
                  )}
                </div>

                {alerts.length > 0 && (
                  <div className="border-t border-slate-100 px-4 py-2.5 bg-slate-50/50">
                    <button
                      onClick={() => { navigate('/alerts'); setIsNotifOpen(false); }}
                      className="w-full text-center text-sm font-medium text-indigo-600 hover:text-indigo-700 transition-colors"
                    >
                      View All Alerts →
                    </button>
                  </div>
                )}
              </div>
            </>
          )}
        </div>
        
        <div className="h-8 w-px bg-slate-200 mx-1"></div>
        
        <div className="relative">
          <button 
            onClick={() => { setIsProfileOpen(!isProfileOpen); setIsNotifOpen(false); }}
            className="flex items-center gap-3 hover:bg-slate-50 p-1.5 pr-3 rounded-xl border border-transparent hover:border-slate-200 transition-all duration-200"
          >
            <div className="w-8 h-8 bg-indigo-100 border border-indigo-200 rounded-lg flex items-center justify-center text-indigo-700 font-medium shadow-sm">
              <User className="w-4 h-4" />
            </div>
            <div className="hidden md:block text-left">
              <p className="text-sm font-medium text-slate-700 leading-none">Admin User</p>
              <p className="text-xs text-slate-500 mt-1 leading-none">Proctor</p>
            </div>
            <ChevronDown className="w-4 h-4 text-slate-400 hidden md:block" />
          </button>

          {isProfileOpen && (
            <>
              <div className="fixed inset-0 z-40" onClick={() => setIsProfileOpen(false)}></div>
              <div className="absolute right-0 mt-2 w-56 bg-white rounded-xl shadow-lg border border-slate-100 py-1.5 z-50 animate-in fade-in slide-in-from-top-2 duration-200">
                <div className="px-4 py-3 border-b border-slate-100 mb-1">
                  <p className="text-sm font-medium text-slate-900">Admin User</p>
                  <p className="text-xs text-slate-500 mt-1">admin@examguard.pro</p>
                </div>
                <button
                  onClick={() => { navigate('/settings'); setIsProfileOpen(false); }}
                  className="w-full text-left px-4 py-2 text-sm text-slate-600 hover:bg-slate-50 hover:text-slate-900 flex items-center gap-2.5 transition-colors"
                >
                  <Settings className="w-4 h-4 text-slate-400" />
                  Account Settings
                </button>
                <div className="h-px bg-slate-100 my-1"></div>
                <button 
                  onClick={logout}
                  className="w-full text-left px-4 py-2 text-sm text-rose-600 hover:bg-rose-50 flex items-center gap-2.5 transition-colors"
                >
                  <LogOut className="w-4 h-4" />
                  Sign out
                </button>
              </div>
            </>
          )}
        </div>
      </div>
    </header>
  );
}
