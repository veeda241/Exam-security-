import { Link, useLocation } from "react-router-dom";
import { LayoutDashboard, Video, Users, AlertTriangle, Menu, X, BarChart3, FileText, Settings, LogOut } from "lucide-react";
import { cn } from "../utils";
import { useState, useEffect } from "react";
import { useAuth } from "../context/AuthContext";
import { motion, AnimatePresence } from "motion/react";

const mainNav = [
  { name: "Home", href: "/", icon: LayoutDashboard },
  { name: "Sessions", href: "/sessions", icon: Video },
  { name: "Students", href: "/students", icon: Users },
  { name: "Alerts", href: "/alerts", icon: AlertTriangle },
];

const moreNav = [
  { name: "Analytics", href: "/analytics", icon: BarChart3 },
  { name: "Reports", href: "/reports", icon: FileText },
];

export function BottomNav() {
  const location = useLocation();
  const { logout } = useAuth();
  const [isMenuOpen, setIsMenuOpen] = useState(false);

  // Close menu when route changes
  useEffect(() => {
    setIsMenuOpen(false);
  }, [location.pathname]);

  return (
    <>
      <div 
        className="md:hidden fixed bottom-0 left-0 right-0 bg-white border-t border-slate-200 flex justify-around items-center z-50"
        style={{ paddingBottom: 'env(safe-area-inset-bottom)', height: 'calc(4rem + env(safe-area-inset-bottom))' }}
      >
        {mainNav.map((item) => {
          const isActive = location.pathname === item.href || (item.href !== "/" && location.pathname.startsWith(item.href));
          return (
            <Link
              key={item.name}
              to={item.href}
              className={cn(
                "flex flex-col items-center justify-center w-full h-full space-y-1",
                isActive ? "text-indigo-600" : "text-slate-500 hover:text-slate-900"
              )}
            >
              <item.icon className={cn("w-5 h-5", isActive ? "text-indigo-600" : "text-slate-400")} />
              <span className="text-[10px] font-medium">{item.name}</span>
            </Link>
          );
        })}
        <button
          onClick={() => setIsMenuOpen(!isMenuOpen)}
          className={cn(
            "flex flex-col items-center justify-center w-full h-full space-y-1",
            isMenuOpen ? "text-indigo-600" : "text-slate-500 hover:text-slate-900"
          )}
        >
          {isMenuOpen ? <X className={cn("w-5 h-5", isMenuOpen ? "text-indigo-600" : "text-slate-400")} /> : <Menu className="w-5 h-5 text-slate-400" />}
          <span className="text-[10px] font-medium">Menu</span>
        </button>
      </div>

      <AnimatePresence>
        {isMenuOpen && (
          <motion.div
            initial={{ opacity: 0, y: "100%" }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: "100%" }}
            transition={{ type: "spring", damping: 25, stiffness: 200 }}
            className="md:hidden fixed inset-0 z-40 bg-slate-50 pt-8 pb-24 px-6 overflow-y-auto"
          >
            <div className="flex items-center justify-between mb-8">
              <h2 className="text-2xl font-bold text-slate-900">Menu</h2>
            </div>
            
            <div className="space-y-3">
              {moreNav.map((item) => {
                const isActive = location.pathname === item.href || (item.href !== "/" && location.pathname.startsWith(item.href));
                return (
                  <Link
                    key={item.name}
                    to={item.href}
                    className={cn(
                      "flex items-center p-4 rounded-2xl transition-colors bg-white border border-slate-200 shadow-sm",
                      isActive ? "ring-2 ring-indigo-500 border-transparent" : "hover:border-indigo-300"
                    )}
                  >
                    <div className={cn("p-2 rounded-xl mr-4", isActive ? "bg-indigo-100 text-indigo-600" : "bg-slate-100 text-slate-500")}>
                      <item.icon className="w-6 h-6" />
                    </div>
                    <span className="font-semibold text-slate-700 text-lg">{item.name}</span>
                  </Link>
                );
              })}
            </div>

            <div className="mt-8 space-y-3">
              <button className="w-full flex items-center p-4 rounded-2xl bg-white border border-slate-200 shadow-sm hover:border-slate-300 transition-colors">
                <div className="p-2 rounded-xl mr-4 bg-slate-100 text-slate-500">
                  <Settings className="w-6 h-6" />
                </div>
                <span className="font-semibold text-slate-700 text-lg">Settings</span>
              </button>
              <button 
                onClick={() => {
                  setIsMenuOpen(false);
                  logout();
                }}
                className="w-full flex items-center p-4 rounded-2xl bg-white border border-rose-100 shadow-sm hover:border-rose-200 transition-colors"
              >
                <div className="p-2 rounded-xl mr-4 bg-rose-50 text-rose-500">
                  <LogOut className="w-6 h-6" />
                </div>
                <span className="font-semibold text-rose-600 text-lg">Logout</span>
              </button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
}
