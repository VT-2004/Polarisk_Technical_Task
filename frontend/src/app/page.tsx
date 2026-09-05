"use client";

import React, { useState } from "react";
import { useRouter } from "next/navigation";
import { 
  ShieldCheck, 
  Sparkles, 
  TrendingUp, 
  Mail, 
  ArrowRight, 
  Lock, 
  FileText, 
  AlertCircle, 
  CheckCircle2, 
  Database,
  ExternalLink,
  Zap
} from "lucide-react";

export default function LandingPage() {
  const router = useRouter();
  const [isDemoLoading, setIsDemoLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const handleConnectGmail = () => {
    // Redirect to FastAPI backend OAuth login endpoint
    window.location.href = "http://localhost:8000/api/auth/login";
  };

  const handleLaunchDemo = async () => {
    setIsDemoLoading(true);
    setErrorMsg(null);
    try {
      const res = await fetch("http://localhost:8000/api/demo/load", {
        method: "POST",
        credentials: "include"
      });
      if (res.ok) {
        router.push("/dashboard");
      } else {
        setErrorMsg("Could not connect to backend server. Make sure the FastAPI backend is running on port 8000.");
      }
    } catch (err) {
      setErrorMsg("Backend connection failed. Ensure backend server is running on http://localhost:8000.");
    } finally {
      setIsDemoLoading(false);
    }
  };

  return (
    <main className="min-h-screen bg-slate-950 text-slate-100 flex flex-col justify-between selection:bg-indigo-500 selection:text-white">
      {/* Top Navbar */}
      <header className="border-b border-slate-800/80 bg-slate-950/60 backdrop-blur-md sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-indigo-600 to-violet-500 flex items-center justify-center shadow-lg shadow-indigo-500/20">
              <Sparkles className="w-5 h-5 text-white" />
            </div>
            <div>
              <span className="font-bold text-lg tracking-tight bg-gradient-to-r from-white via-slate-100 to-slate-400 bg-clip-text text-transparent">
                Gmail Spend Intelligence
              </span>
              <span className="ml-2 text-xs px-2 py-0.5 rounded-full bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 font-medium">
                AI Powered
              </span>
            </div>
          </div>

          <div className="flex items-center space-x-3">
            <button
              onClick={handleLaunchDemo}
              disabled={isDemoLoading}
              className="text-sm px-4 py-2 rounded-lg border border-slate-700 bg-slate-900/80 hover:bg-slate-800 text-slate-300 font-medium transition-colors flex items-center space-x-2"
            >
              <Zap className="w-4 h-4 text-amber-400" />
              <span>{isDemoLoading ? "Loading Demo..." : "Quick Demo Mode"}</span>
            </button>
            <button
              onClick={handleConnectGmail}
              className="text-sm px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white font-semibold transition-all shadow-md shadow-indigo-600/20 flex items-center space-x-2"
            >
              <Mail className="w-4 h-4" />
              <span>Connect Gmail</span>
            </button>
          </div>
        </div>
      </header>

      {/* Hero Section */}
      <section className="relative overflow-hidden pt-16 pb-20 px-4 sm:px-6 lg:px-8 max-w-6xl mx-auto flex-1 flex flex-col justify-center items-center text-center">
        {/* Decorative background glow */}
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[350px] bg-indigo-600/15 blur-[120px] rounded-full pointer-events-none -z-10" />

        {errorMsg && (
          <div className="mb-8 p-4 bg-rose-950/50 border border-rose-800/80 text-rose-200 rounded-xl text-sm flex items-center space-x-3 max-w-xl">
            <AlertCircle className="w-5 h-5 text-rose-400 shrink-0" />
            <span>{errorMsg}</span>
          </div>
        )}

        <div className="inline-flex items-center space-x-2 px-3 py-1.5 rounded-full bg-slate-900 border border-slate-800 text-xs font-medium text-slate-300 mb-8 shadow-inner">
          <ShieldCheck className="w-4 h-4 text-emerald-400" />
          <span>Strict Read-Only Permission • Zero Raw Email Persistence</span>
        </div>

        <h1 className="text-4xl sm:text-6xl font-extrabold tracking-tight text-white max-w-4xl leading-[1.15]">
          Turn your inbox receipts into{" "}
          <span className="bg-gradient-to-r from-indigo-400 via-violet-300 to-purple-400 bg-clip-text text-transparent">
            instant financial intelligence
          </span>
        </h1>

        <p className="mt-6 text-lg sm:text-xl text-slate-400 max-w-2xl leading-relaxed">
          Connect your Gmail account to scan invoices, bills, and payment confirmations. 
          Extract structured spending data, detect subscription price jumps, and spot anomalies with 100% email traceability.
        </p>

        {/* CTA Buttons */}
        <div className="mt-10 flex flex-col sm:flex-row items-center gap-4 w-full sm:w-auto">
          <button
            onClick={handleConnectGmail}
            className="w-full sm:w-auto px-8 py-4 rounded-xl bg-gradient-to-r from-indigo-600 to-violet-600 hover:from-indigo-500 hover:to-violet-500 text-white font-semibold text-base shadow-xl shadow-indigo-500/25 transition-all flex items-center justify-center space-x-3 group cursor-pointer"
          >
            <Mail className="w-5 h-5 text-indigo-200" />
            <span>Connect Gmail with Google OAuth</span>
            <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
          </button>

          <button
            onClick={handleLaunchDemo}
            disabled={isDemoLoading}
            className="w-full sm:w-auto px-6 py-4 rounded-xl bg-slate-900 border border-slate-800 hover:bg-slate-800/80 text-slate-200 font-medium text-base transition-colors flex items-center justify-center space-x-2 cursor-pointer"
          >
            <Zap className="w-5 h-5 text-amber-400" />
            <span>{isDemoLoading ? "Generating Demo..." : "Explore Demo Mode (No Login)"}</span>
          </button>
        </div>

        {/* Live Example Insights Preview Cards */}
        <div className="mt-16 w-full max-w-4xl text-left">
          <h2 className="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-4 text-center">
            Example Insights Detected by the Engine
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800/80 shadow-sm hover:border-slate-700 transition-colors">
              <div className="flex items-center space-x-2 text-indigo-400 text-xs font-semibold mb-2">
                <TrendingUp className="w-4 h-4" />
                <span>CATEGORY LEADER</span>
              </div>
              <p className="text-sm text-slate-200 font-medium">
                &ldquo;You spent ₹42,000 on travel this month, which is your highest spending category.&rdquo;
              </p>
              <div className="mt-3 text-xs text-slate-500 flex items-center space-x-1">
                <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                <span>MakeMyTrip Booking</span>
              </div>
            </div>

            <div className="p-4 rounded-xl bg-slate-900/60 border border-amber-900/40 bg-amber-950/10 shadow-sm hover:border-amber-700/50 transition-colors">
              <div className="flex items-center space-x-2 text-amber-400 text-xs font-semibold mb-2">
                <AlertCircle className="w-4 h-4" />
                <span>PRICE JUMP ANOMALY</span>
              </div>
              <p className="text-sm text-slate-200 font-medium">
                &ldquo;Your latest Adobe payment of ₹6,899 is 64% higher than your previous average of ₹4,200.&rdquo;
              </p>
              <div className="mt-3 text-xs text-slate-500 flex items-center space-x-1">
                <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                <span>Adobe Creative Cloud</span>
              </div>
            </div>

            <div className="p-4 rounded-xl bg-slate-900/60 border border-rose-900/40 bg-rose-950/10 shadow-sm hover:border-rose-700/50 transition-colors">
              <div className="flex items-center space-x-2 text-rose-400 text-xs font-semibold mb-2">
                <Zap className="w-4 h-4" />
                <span>UNSEEN HIGH MERCHANT</span>
              </div>
              <p className="text-sm text-slate-200 font-medium">
                &ldquo;A ₹35,000 payment to Taj Palace was flagged because this merchant has not appeared before.&rdquo;
              </p>
              <div className="mt-3 text-xs text-slate-500 flex items-center space-x-1">
                <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                <span>Taj Palace & Resorts</span>
              </div>
            </div>
          </div>
        </div>

        {/* Security & Privacy Pillars */}
        <div className="mt-16 pt-10 border-t border-slate-900 w-full grid grid-cols-1 sm:grid-cols-3 gap-6 text-left">
          <div className="flex items-start space-x-3">
            <div className="p-2 rounded-lg bg-indigo-500/10 border border-indigo-500/20 text-indigo-400 shrink-0">
              <Lock className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-sm font-semibold text-white">Read-Only Scope</h3>
              <p className="mt-1 text-xs text-slate-400">
                Only requests <code className="text-indigo-300">gmail.readonly</code>. Cannot write, modify, or send emails.
              </p>
            </div>
          </div>

          <div className="flex items-start space-x-3">
            <div className="p-2 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 shrink-0">
              <Database className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-sm font-semibold text-white">No Email Body Storage</h3>
              <p className="mt-1 text-xs text-slate-400">
                Only extracted numerical transaction data is saved in local SQLite. Trace directly via Gmail links.
              </p>
            </div>
          </div>

          <div className="flex items-start space-x-3">
            <div className="p-2 rounded-lg bg-violet-500/10 border border-violet-500/20 text-violet-400 shrink-0">
              <FileText className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-sm font-semibold text-white">1-Click Data Purge</h3>
              <p className="mt-1 text-xs text-slate-400">
                Instantly revoke tokens and wipe all local transaction data with a single button.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-slate-900 py-6 px-4 text-center text-xs text-slate-400">
        <p>Gmail Spend Intelligence • Built for Polarisk Technical Assessment</p>
      </footer>
    </main>
  );
}
