import React, { useState } from "react";
import { UserPlus, Mail, BookOpen, Fingerprint, Camera, CheckCircle2 } from "lucide-react";
import { motion } from "motion/react";
import WebcamCapture from "./WebcamCapture";

export function StudentRegistration() {
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isSuccess, setIsSuccess] = useState(false);
  const [capturedPhoto, setCapturedPhoto] = useState<string | null>(null);
  const [cameraReady, setCameraReady] = useState(false);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    // Simulate API call
    setTimeout(() => {
      setIsSubmitting(false);
      setIsSuccess(true);
      setTimeout(() => setIsSuccess(false), 3000);
    }, 1500);
  };

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Student Registration</h1>
        <p className="text-slate-500 mt-1 text-sm">Enroll a new student and set up their proctoring profile.</p>
      </div>

      <form onSubmit={handleSubmit}>
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <motion.div 
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="lg:col-span-2 bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden"
          >
            <div className="p-6 border-b border-slate-200 bg-slate-50/50">
              <h2 className="text-base font-semibold text-slate-900">Personal Information</h2>
              <p className="text-sm text-slate-500 mt-1">Basic details for the student profile.</p>
            </div>
            <div className="p-6 space-y-6">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
                <div className="space-y-2">
                  <label className="text-sm font-medium text-slate-700">First Name</label>
                  <div className="relative">
                    <UserPlus className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                    <input required type="text" className="w-full pl-10 pr-4 py-2.5 rounded-xl border border-slate-200 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-all bg-white text-slate-900 placeholder:text-slate-400" placeholder="e.g. Jane" />
                  </div>
                </div>
                <div className="space-y-2">
                  <label className="text-sm font-medium text-slate-700">Last Name</label>
                  <div className="relative">
                    <UserPlus className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                    <input required type="text" className="w-full pl-10 pr-4 py-2.5 rounded-xl border border-slate-200 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-all bg-white text-slate-900 placeholder:text-slate-400" placeholder="e.g. Doe" />
                  </div>
                </div>
              </div>

              <div className="space-y-2">
                <label className="text-sm font-medium text-slate-700">Email Address</label>
                <div className="relative">
                  <Mail className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                  <input required type="email" className="w-full pl-10 pr-4 py-2.5 rounded-xl border border-slate-200 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-all bg-white text-slate-900 placeholder:text-slate-400" placeholder="jane.doe@university.edu" />
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
                <div className="space-y-2">
                  <label className="text-sm font-medium text-slate-700">Student ID</label>
                  <div className="relative">
                    <Fingerprint className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                    <input required type="text" className="w-full pl-10 pr-4 py-2.5 rounded-xl border border-slate-200 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-all bg-white text-slate-900 placeholder:text-slate-400" placeholder="e.g. STU-2024-001" />
                  </div>
                </div>
                <div className="space-y-2">
                  <label className="text-sm font-medium text-slate-700">Primary Course</label>
                  <div className="relative">
                    <BookOpen className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                    <select required className="w-full pl-10 pr-4 py-2.5 rounded-xl border border-slate-200 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-all appearance-none bg-white text-slate-900 cursor-pointer">
                      <option value="" disabled selected>Select course...</option>
                      <option>Computer Science</option>
                      <option>Mathematics</option>
                      <option>Physics</option>
                      <option>English Literature</option>
                    </select>
                  </div>
                </div>
              </div>
            </div>
          </motion.div>

          <motion.div 
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 }}
            className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden flex flex-col"
          >
            <div className="p-6 border-b border-slate-200 bg-slate-50/50">
              <h2 className="text-base font-semibold text-slate-900">Identity Verification</h2>
              <p className="text-sm text-slate-500 mt-1">Capture a live reference image with the webcam.</p>
            </div>
            <div className="p-6 flex-1 flex flex-col gap-4">
              <div className="rounded-2xl border border-slate-200 bg-slate-950 p-3 shadow-inner">
                <WebcamCapture
                  width={320}
                  height={240}
                  onCapture={(imageSrc) => setCapturedPhoto(imageSrc)}
                  onUserMedia={() => setCameraReady(true)}
                />
              </div>

              <div className="rounded-xl border border-slate-200 bg-slate-50 p-4">
                <div className="flex items-center justify-between gap-3">
                  <div>
                    <p className="text-sm font-semibold text-slate-900">Captured reference</p>
                    <p className="text-xs text-slate-500 mt-1">
                      {cameraReady ? 'Camera ready. Capture a still photo to save the reference.' : 'Allow camera access to continue.'}
                    </p>
                  </div>
                  <div className="inline-flex items-center gap-2 text-xs font-medium px-3 py-1.5 rounded-full bg-white border border-slate-200 text-slate-600">
                    <Camera className="w-3.5 h-3.5" />
                    {cameraReady ? 'Ready' : 'Waiting'}
                  </div>
                </div>

                <div className="mt-4 rounded-xl overflow-hidden border border-dashed border-slate-200 bg-white min-h-40 flex items-center justify-center">
                  {capturedPhoto ? (
                    <img
                      src={capturedPhoto}
                      alt="Captured webcam reference"
                      className="w-full h-full object-cover"
                    />
                  ) : (
                    <div className="text-center px-6 py-8 text-slate-400">
                      <Camera className="w-10 h-10 mx-auto mb-3 opacity-40" />
                      <p className="text-sm">No webcam capture yet</p>
                    </div>
                  )}
                </div>
              </div>
            </div>
          </motion.div>
        </div>

        <div className="mt-8 flex items-center justify-end gap-4 pt-6 border-t border-slate-200">
          <button type="button" className="px-5 py-2.5 rounded-xl text-sm font-medium text-slate-600 hover:bg-slate-100 hover:text-slate-900 transition-colors">
            Cancel
          </button>
          <button 
            type="submit" 
            disabled={isSubmitting || isSuccess}
            className={`relative inline-flex items-center justify-center px-6 py-2.5 rounded-xl text-sm font-semibold text-white transition-all active:scale-95 overflow-hidden shadow-sm ${
              isSuccess ? 'bg-emerald-500 hover:bg-emerald-600' : 'bg-indigo-600 hover:bg-indigo-700'
            }`}
          >
            {isSubmitting ? (
              <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
            ) : isSuccess ? (
              <>
                <CheckCircle2 className="w-4 h-4 mr-2" />
                Registered
              </>
            ) : (
              'Register Student'
            )}
          </button>
        </div>
      </form>
    </div>
  );
}
