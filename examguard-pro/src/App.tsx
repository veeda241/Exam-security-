/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React from "react";
import { BrowserRouter, Routes, Route, Navigate, Outlet, useLocation } from "react-router-dom";
import { AuthProvider, useAuth } from "./context/AuthContext";
import { AppProvider } from "./context/AppContext";
import { Sidebar } from "./components/Sidebar";
import { Header } from "./components/Header";
import { Dashboard } from "./components/Dashboard";
import { Sessions } from "./components/Sessions";
import { SessionDetail } from "./components/SessionDetail";
import { Alerts } from "./components/Alerts";
import { Analytics } from "./components/Analytics";
import { Reports } from "./components/Reports";
import { Students } from "./components/Students";
import { Login } from "./components/Login";
import { StudentRegistration } from "./components/StudentRegistration";
import { StudentDetail } from "./components/StudentDetail";
import { Settings } from "./components/Settings";
import { ToastContainer } from "./components/ToastContainer";
import { BottomNav } from "./components/BottomNav";
import { motion, AnimatePresence } from "motion/react";
import "./App.css";

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { isAuthenticated } = useAuth();
  return isAuthenticated ? <>{children}</> : <Navigate to="/login" />;
}

function PageWrapper() {
  const location = useLocation();
  return (
    <AnimatePresence mode="wait">
      <motion.div
        key={location.pathname}
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0, y: -10 }}
        transition={{ duration: 0.2 }}
        className="h-full"
      >
        <Outlet />
      </motion.div>
    </AnimatePresence>
  );
}

function AppLayout() {
  return (
    <div className="app-container bg-slate-50 text-slate-900">
      <Sidebar />
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden relative">
        <Header />
        <main className="flex-1 overflow-y-auto p-4 sm:p-6 relative pb-24 md:pb-6">
          <PageWrapper />
        </main>
      </div>
      <BottomNav />
      <ToastContainer />
    </div>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <AppProvider>
        <AuthProvider>
          <Routes>
            <Route path="/login" element={<Login />} />
            <Route path="/register" element={<StudentRegistration />} />
            <Route path="/" element={<ProtectedRoute><AppLayout /></ProtectedRoute>}>
              <Route index element={<Dashboard />} />
              <Route path="sessions" element={<Sessions />} />
              <Route path="sessions/:sessionId" element={<SessionDetail />} />
              <Route path="students" element={<Students />} />
              <Route path="student/:studentId" element={<StudentDetail />} />
              <Route path="alerts" element={<Alerts />} />
              <Route path="analytics" element={<Analytics />} />
              <Route path="reports" element={<Reports />} />
              <Route path="settings" element={<Settings />} />
            </Route>
          </Routes>
        </AuthProvider>
      </AppProvider>
    </BrowserRouter>
  );
}
