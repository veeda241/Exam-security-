import React, { useState } from "react";
import { User, Lock, Check, Eye, EyeOff, LogOut } from "lucide-react";
import { useAuth } from "../context/AuthContext";
import { config } from "../config";
import { useNavigate } from "react-router-dom";

export function Settings() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  // Password
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [showCurrentPw, setShowCurrentPw] = useState(false);
  const [showNewPw, setShowNewPw] = useState(false);
  const [pwStatus, setPwStatus] = useState<"idle" | "success" | "error">("idle");
  const [pwError, setPwError] = useState("");

  const handleChangePassword = async (e: React.FormEvent) => {
    e.preventDefault();
    if (newPassword !== confirmPassword) {
      setPwStatus("error");
      setPwError("Passwords do not match");
      return;
    }
    try {
      const token = localStorage.getItem("token");
      const res = await fetch(`${config.apiUrl}/auth/change-password`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({
          current_password: currentPassword,
          new_password: newPassword,
        }),
      });
      if (res.ok) {
        setPwStatus("success");
        setCurrentPassword("");
        setNewPassword("");
        setConfirmPassword("");
        setTimeout(() => setPwStatus("idle"), 3000);
      } else {
        const data = await res.json();
        setPwStatus("error");
        setPwError(data.detail || "Failed to change password");
      }
    } catch {
      setPwStatus("error");
      setPwError("Network error. Is the server running?");
    }
  };

  const handleLogout = () => {
    logout();
    navigate("/login");
  };

  return (
    <div className="space-y-6 max-w-3xl mx-auto">
      <div>
        <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Account Settings</h1>
        <p className="text-slate-500 mt-1">Manage your profile and security.</p>
      </div>

      {/* Profile Section */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
        <div className="p-5 border-b border-slate-200 bg-slate-50/50 flex items-center gap-3">
          <div className="p-2 rounded-lg bg-indigo-50 text-indigo-600 border border-indigo-100">
            <User className="w-4 h-4" />
          </div>
          <h2 className="font-semibold text-slate-900">Profile</h2>
        </div>
        <div className="p-6">
          <div className="flex items-center gap-5">
            <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center text-white text-xl font-bold shadow-lg">
              {(user?.username || "A").charAt(0).toUpperCase()}
            </div>
            <div>
              <p className="text-lg font-semibold text-slate-900">{user?.username || "Admin"}</p>
              <p className="text-sm text-slate-500">Administrator</p>
            </div>
          </div>
        </div>
      </div>

      {/* Change Password */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
        <div className="p-5 border-b border-slate-200 bg-slate-50/50 flex items-center gap-3">
          <div className="p-2 rounded-lg bg-amber-50 text-amber-600 border border-amber-100">
            <Lock className="w-4 h-4" />
          </div>
          <h2 className="font-semibold text-slate-900">Change Password</h2>
        </div>
        <form onSubmit={handleChangePassword} className="p-6 space-y-5">
          <div className="space-y-1.5">
            <label className="text-sm font-medium text-slate-700">Current Password</label>
            <div className="relative">
              <input
                type={showCurrentPw ? "text" : "password"}
                value={currentPassword}
                onChange={(e) => { setCurrentPassword(e.target.value); setPwStatus("idle"); }}
                required
                className="w-full px-4 py-2.5 pr-11 rounded-xl border border-slate-200 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-all bg-white text-slate-900"
                placeholder="Enter your current password"
              />
              <button
                type="button"
                onClick={() => setShowCurrentPw(!showCurrentPw)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"
              >
                {showCurrentPw ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
              </button>
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="space-y-1.5">
              <label className="text-sm font-medium text-slate-700">New Password</label>
              <div className="relative">
                <input
                  type={showNewPw ? "text" : "password"}
                  value={newPassword}
                  onChange={(e) => { setNewPassword(e.target.value); setPwStatus("idle"); }}
                  required
                  minLength={6}
                  className="w-full px-4 py-2.5 pr-11 rounded-xl border border-slate-200 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-all bg-white text-slate-900"
                  placeholder="Min 6 characters"
                />
                <button
                  type="button"
                  onClick={() => setShowNewPw(!showNewPw)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"
                >
                  {showNewPw ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
            </div>
            <div className="space-y-1.5">
              <label className="text-sm font-medium text-slate-700">Confirm Password</label>
              <input
                type="password"
                value={confirmPassword}
                onChange={(e) => { setConfirmPassword(e.target.value); setPwStatus("idle"); }}
                required
                className="w-full px-4 py-2.5 rounded-xl border border-slate-200 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-all bg-white text-slate-900"
                placeholder="Repeat new password"
              />
            </div>
          </div>

          {pwStatus === "success" && (
            <div className="flex items-center gap-2 text-sm text-emerald-600 bg-emerald-50 border border-emerald-200 px-4 py-2.5 rounded-xl">
              <Check className="w-4 h-4" /> Password updated successfully!
            </div>
          )}
          {pwStatus === "error" && (
            <div className="text-sm text-rose-600 bg-rose-50 border border-rose-200 px-4 py-2.5 rounded-xl">
              {pwError}
            </div>
          )}

          <div className="flex justify-end pt-2">
            <button
              type="submit"
              className="inline-flex items-center justify-center gap-2 rounded-xl bg-indigo-600 px-5 py-2.5 text-sm font-semibold text-white hover:bg-indigo-700 transition-colors shadow-sm active:scale-95"
            >
              <Lock className="w-4 h-4" />
              Update Password
            </button>
          </div>
        </form>
      </div>

      {/* Sign Out */}
      <div className="bg-white rounded-2xl border border-rose-200 shadow-sm overflow-hidden">
        <div className="p-6 flex items-center justify-between">
          <div>
            <p className="text-sm font-medium text-slate-900">Sign Out</p>
            <p className="text-xs text-slate-500 mt-0.5">End your session and return to the login screen.</p>
          </div>
          <button
            onClick={handleLogout}
            className="inline-flex items-center gap-2 rounded-xl border border-rose-200 bg-white px-4 py-2.5 text-sm font-semibold text-rose-600 hover:bg-rose-50 transition-colors active:scale-95"
          >
            <LogOut className="w-4 h-4" />
            Sign Out
          </button>
        </div>
      </div>
    </div>
  );
}
