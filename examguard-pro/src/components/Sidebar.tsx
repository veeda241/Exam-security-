import { Link, useLocation } from "react-router-dom";
import { 
  LayoutDashboard, 
  Video, 
  AlertTriangle, 
  BarChart3, 
  FileText, 
  Settings,
  LogOut,
  Users,
  ShieldCheck
} from "lucide-react";
import { cn } from "../utils";
import { useAuth } from "../context/AuthContext";

const navigation = [
  { name: "Dashboard", href: "/", icon: LayoutDashboard },
  { name: "Sessions", href: "/sessions", icon: Video },
  { name: "Students", href: "/students", icon: Users },
  { name: "Alerts", href: "/alerts", icon: AlertTriangle },
  { name: "Analytics", href: "/analytics", icon: BarChart3 },
  { name: "Reports", href: "/reports", icon: FileText },
];

export function Sidebar() {
  const location = useLocation();
  const { logout } = useAuth();

  return (
    <div className="hidden md:flex h-full w-64 flex-col bg-white border-r border-slate-200 text-slate-700 shrink-0">
      <div className="flex h-16 items-center px-6 border-b border-slate-200">
        <div className="flex items-center gap-3 font-bold text-lg tracking-tight text-slate-900">
          <div className="bg-indigo-50 border border-indigo-100 p-1.5 rounded-lg shadow-sm">
            <ShieldCheck className="w-5 h-5 text-indigo-600" />
          </div>
          <span>Exam<span className="text-indigo-600">Guard</span></span>
        </div>
      </div>
      <div className="flex-1 overflow-y-auto py-6">
        <nav className="space-y-1 px-3">
          {navigation.map((item) => {
            const isActive = location.pathname === item.href || (item.href !== "/" && location.pathname.startsWith(item.href));
            return (
              <Link
                key={item.name}
                to={item.href}
                className={cn(
                  isActive
                    ? "bg-indigo-50 text-indigo-600 font-semibold"
                    : "text-slate-600 hover:bg-slate-50 hover:text-slate-900",
                  "group flex items-center px-3 py-2.5 text-sm font-medium rounded-xl transition-all duration-200"
                )}
              >
                <item.icon
                  className={cn(
                    isActive ? "text-indigo-600" : "text-slate-400 group-hover:text-slate-600",
                    "mr-3 h-5 w-5 flex-shrink-0 transition-colors duration-200"
                  )}
                  aria-hidden="true"
                />
                {item.name}
              </Link>
            );
          })}
        </nav>
      </div>
      <div className="border-t border-slate-200 p-4">
        <Link
          to="/settings"
          className={cn(
            location.pathname === '/settings'
              ? "bg-indigo-50 text-indigo-600 font-semibold"
              : "text-slate-600 hover:bg-slate-50 hover:text-slate-900",
            "flex items-center gap-3 px-3 py-2.5 text-sm font-medium rounded-xl cursor-pointer transition-all duration-200"
          )}
        >
          <Settings className={cn(
            location.pathname === '/settings' ? "text-indigo-600" : "text-slate-400",
            "h-5 w-5"
          )} />
          <span>Settings</span>
        </Link>
        <div 
          onClick={logout}
          className="flex items-center gap-3 px-3 py-2.5 text-sm font-medium text-slate-600 hover:bg-rose-50 hover:text-rose-600 rounded-xl cursor-pointer transition-all duration-200 mt-1 group"
        >
          <LogOut className="h-5 w-5 text-slate-400 group-hover:text-rose-500 transition-colors" />
          <span>Logout</span>
        </div>
      </div>
    </div>
  );
}
