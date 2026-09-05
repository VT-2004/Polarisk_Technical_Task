"use client";

import React, { useEffect, useState, useMemo } from "react";
import { useRouter } from "next/navigation";
import { 
  Sparkles, 
  RefreshCw, 
  Trash2, 
  ExternalLink, 
  TrendingUp, 
  AlertTriangle, 
  CreditCard, 
  Calendar, 
  Search, 
  Filter, 
  ShieldCheck, 
  ArrowLeft,
  DollarSign,
  PieChart,
  Repeat,
  CheckCircle,
  AlertCircle,
  Clock,
  Layers,
  Zap,
  Info,
  LogOut,
  Lock,
  X,
  History,
  FolderGit2,
  Plus
} from "lucide-react";

interface Transaction {
  id: number;
  message_id: string;
  subject: string;
  sender: string;
  merchant: string;
  amount: number;
  currency: string;
  date: string;
  category: string;
  transaction_type: string;
  confidence: string;
  gmail_permalink: string;
  snippet?: string;
}

interface CategoryItem {
  category: string;
  total: number;
  count: number;
  percentage: number;
}

interface MerchantItem {
  merchant: string;
  total: number;
  count: number;
}

interface MonthlyTrend {
  month: string;
  total: number;
}

interface RecurringSubscription {
  merchant: string;
  cadence: string;
  average_amount: number;
  latest_amount: number;
  latest_date: string;
  frequency_count: number;
  currency: string;
  category: string;
  latest_message_id?: string;
  gmail_permalink?: string;
}

interface AnomalyFlag {
  id: number;
  flag_type: string;
  severity: "info" | "warning" | "alert";
  title: string;
  reason_data: any;
  explanation: string;
  source_message_id?: string;
  gmail_permalink?: string;
}

interface ScanRunItem {
  id: number;
  run_name: string;
  scan_type: string;
  total_spend: number;
  transaction_count: number;
  anomaly_count: number;
  created_at: string;
}

interface DashboardData {
  user_email: string;
  active_run?: {
    id: number;
    run_name: string;
    created_at: string;
  };
  available_runs: ScanRunItem[];
  summary: {
    total_spend: number;
    currency: string;
    transaction_count: number;
    categories: CategoryItem[];
    merchants: MerchantItem[];
    monthly_trends: MonthlyTrend[];
  };
  recurring_subscriptions: RecurringSubscription[];
  anomalies: AnomalyFlag[];
  transactions: Transaction[];
}

interface ScanProgress {
  is_scanning: boolean;
  stage: string;
  message: string;
  scanned_count: number;
  total_count: number;
  extracted_count: number;
  error?: string;
}

const CATEGORY_COLORS: Record<string, { bg: string; text: string; bar: string }> = {
  travel: { bg: "bg-blue-500/10", text: "text-blue-400", bar: "bg-blue-500" },
  subscriptions: { bg: "bg-purple-500/10", text: "text-purple-400", bar: "bg-purple-500" },
  software: { bg: "bg-indigo-500/10", text: "text-indigo-400", bar: "bg-indigo-500" },
  food: { bg: "bg-orange-500/10", text: "text-orange-400", bar: "bg-orange-500" },
  shopping: { bg: "bg-emerald-500/10", text: "text-emerald-400", bar: "bg-emerald-500" },
  utilities: { bg: "bg-cyan-500/10", text: "text-cyan-400", bar: "bg-cyan-500" },
  entertainment: { bg: "bg-pink-500/10", text: "text-pink-400", bar: "bg-pink-500" },
  other: { bg: "bg-slate-500/10", text: "text-slate-400", bar: "bg-slate-500" }
};

export default function DashboardPage() {
  const router = useRouter();
  const [data, setData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [scanProgress, setScanProgress] = useState<ScanProgress | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedCategory, setSelectedCategory] = useState("all");
  const [isPurging, setIsPurging] = useState(false);
  const [isScanning, setIsScanning] = useState(false);
  const [showPrivacyModal, setShowPrivacyModal] = useState(false);
  const [selectedRunId, setSelectedRunId] = useState<number | null>(null);

  // Format currency helper
  const formatCurrency = (amount: number, currency: string = "INR") => {
    const symbol = currency === "INR" ? "₹" : (currency === "USD" ? "$" : (currency === "EUR" ? "€" : currency));
    return `${symbol}${amount.toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  };

  const fetchDashboard = async (runId?: number | null) => {
    try {
      setLoading(true);
      setError(null);
      const url = runId 
        ? `http://localhost:8000/api/dashboard?run_id=${runId}` 
        : "http://localhost:8000/api/dashboard";

      const res = await fetch(url, {
        credentials: "include"
      });

      if (res.status === 401) {
        router.push("/?error=unauthorized");
        return;
      }

      if (!res.ok) {
        throw new Error("Failed to load dashboard data");
      }

      const jsonData = await res.json();
      setData(jsonData);
      if (jsonData.active_run?.id) {
        setSelectedRunId(jsonData.active_run.id);
      }
    } catch (err: any) {
      setError(err.message || "Failed to load dashboard");
    } finally {
      setLoading(false);
    }
  };

  const pollScanProgress = async () => {
    try {
      const res = await fetch("http://localhost:8000/api/scan/progress", {
        credentials: "include"
      });
      if (res.ok) {
        const progress: ScanProgress = await res.json();
        setScanProgress(progress);
        setIsScanning(progress.is_scanning);

        if (progress.is_scanning) {
          setTimeout(pollScanProgress, 1500);
        } else if (progress.stage === "complete") {
          fetchDashboard();
        }
      }
    } catch (e) {
      // Ignore polling errors
    }
  };

  const triggerScan = async () => {
    setIsScanning(true);
    try {
      const res = await fetch("http://localhost:8000/api/scan", {
        method: "POST",
        credentials: "include"
      });
      if (res.ok) {
        pollScanProgress();
      }
    } catch (e) {
      setIsScanning(false);
    }
  };

  const handleDeleteRun = async (runId: number, e: React.MouseEvent) => {
    e.stopPropagation();
    if (!confirm("Are you sure you want to delete this specific test scan result?")) {
      return;
    }
    try {
      await fetch(`http://localhost:8000/api/runs/${runId}`, {
        method: "DELETE",
        credentials: "include"
      });
      fetchDashboard();
    } catch (e) {
      alert("Failed to delete scan result");
    }
  };

  const handleLogout = async () => {
    try {
      await fetch("http://localhost:8000/api/auth/logout", {
        method: "POST",
        credentials: "include"
      });
      router.push("/");
    } catch (e) {
      router.push("/");
    }
  };

  const handleRevokeGoogleAccess = async () => {
    if (!confirm("Are you sure you want to STOP sharing and formally revoke Google OAuth permissions? This will unlink your Gmail account on Google's servers and permanently delete all your stored financial intelligence.")) {
      return;
    }
    setIsPurging(true);
    try {
      await fetch("http://localhost:8000/api/auth/revoke", {
        method: "POST",
        credentials: "include"
      });
      alert("Google access has been formally revoked and all data deleted.");
      router.push("/");
    } catch (e) {
      alert("Failed to revoke access");
    } finally {
      setIsPurging(false);
    }
  };

  useEffect(() => {
    fetchDashboard();
    pollScanProgress();
  }, []);

  // Filtered transactions list
  const filteredTransactions = useMemo(() => {
    if (!data?.transactions) return [];
    return data.transactions.filter(tx => {
      const matchesSearch = 
        tx.merchant.toLowerCase().includes(searchQuery.toLowerCase()) ||
        (tx.subject && tx.subject.toLowerCase().includes(searchQuery.toLowerCase())) ||
        (tx.snippet && tx.snippet.toLowerCase().includes(searchQuery.toLowerCase()));
      const matchesCat = selectedCategory === "all" || tx.category.toLowerCase() === selectedCategory.toLowerCase();
      return matchesSearch && matchesCat;
    });
  }, [data, searchQuery, selectedCategory]);

  if (loading && !data) {
    return (
      <div className="min-h-screen bg-slate-950 text-slate-100 flex items-center justify-center">
        <div className="flex flex-col items-center space-y-4">
          <div className="w-12 h-12 rounded-full border-4 border-indigo-500/20 border-t-indigo-500 animate-spin" />
          <p className="text-slate-400 font-medium">Loading Spend Intelligence...</p>
        </div>
      </div>
    );
  }

  const currency = data?.summary.currency || "INR";
  const totalSpend = data?.summary.total_spend || 0;
  const topCategory = data?.summary.categories[0];
  const topMerchant = data?.summary.merchants[0];
  const anomalyCount = data?.anomalies.length || 0;
  const availableRuns = data?.available_runs || [];

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col">
      {/* Top Navbar */}
      <header className="border-b border-slate-800/80 bg-slate-950/80 backdrop-blur-md sticky top-0 z-40">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <button
              onClick={() => router.push("/")}
              className="p-2 rounded-lg hover:bg-slate-900 text-slate-400 hover:text-white transition-colors"
              title="Back to home"
            >
              <ArrowLeft className="w-5 h-5" />
            </button>
            <div className="w-8 h-8 rounded-lg bg-gradient-to-tr from-indigo-600 to-violet-500 flex items-center justify-center">
              <Sparkles className="w-4 h-4 text-white" />
            </div>
            <div>
              <span className="font-bold text-base bg-gradient-to-r from-white via-slate-100 to-slate-400 bg-clip-text text-transparent">
                Gmail Spend Intelligence
              </span>
              <span className="ml-2 text-xs text-slate-400 hidden sm:inline">
                ({data?.user_email})
              </span>
            </div>
          </div>

          <div className="flex items-center space-x-2.5">
            <button
              onClick={triggerScan}
              disabled={isScanning}
              className="text-xs px-3.5 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white font-semibold transition-all flex items-center space-x-1.5 cursor-pointer disabled:opacity-50 shadow-sm shadow-indigo-600/20"
            >
              <Plus className="w-3.5 h-3.5" />
              <span>{isScanning ? "Scanning..." : "Run New Scan"}</span>
            </button>

            <button
              onClick={() => setShowPrivacyModal(true)}
              className="text-xs px-3 py-1.5 rounded-lg bg-slate-900 border border-slate-700 hover:bg-slate-800 text-slate-200 font-medium transition-colors flex items-center space-x-1.5 cursor-pointer"
              title="Privacy settings and Google OAuth permissions"
            >
              <Lock className="w-3.5 h-3.5 text-emerald-400" />
              <span className="hidden sm:inline">Privacy & Permissions</span>
            </button>

            <button
              onClick={handleLogout}
              className="text-xs px-3 py-1.5 rounded-lg bg-slate-900 border border-slate-800 hover:bg-slate-800 text-slate-400 hover:text-slate-200 font-medium transition-colors flex items-center space-x-1.5 cursor-pointer"
              title="Log out from current session"
            >
              <LogOut className="w-3.5 h-3.5" />
              <span className="hidden sm:inline">Log Out</span>
            </button>
          </div>
        </div>
      </header>

      {/* Main Content Area */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
        
        {/* Isolated Scan Results History Switcher */}
        {availableRuns.length > 0 && (
          <div className="p-4 rounded-2xl bg-slate-900/60 border border-slate-800/80 space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-2">
                <History className="w-4 h-4 text-indigo-400" />
                <span className="text-xs font-bold uppercase tracking-wider text-slate-300">
                  Scan History & Test Results
                </span>
                <span className="text-xs text-slate-500">
                  (Select a run to view isolated analytics without overlap)
                </span>
              </div>
              <span className="text-xs text-slate-400 font-mono">
                {availableRuns.length} Total Run{availableRuns.length > 1 ? "s" : ""} Saved
              </span>
            </div>

            <div className="flex items-center gap-2 overflow-x-auto pb-1 scrollbar-thin">
              {availableRuns.map((run) => {
                const isActive = data?.active_run?.id === run.id;
                return (
                  <div
                    key={run.id}
                    onClick={() => {
                      setSelectedRunId(run.id);
                      fetchDashboard(run.id);
                    }}
                    className={`px-3.5 py-2 rounded-xl text-xs font-medium cursor-pointer transition-all flex items-center space-x-2.5 shrink-0 border ${
                      isActive
                        ? "bg-indigo-600/20 border-indigo-500 text-indigo-200 shadow-md shadow-indigo-600/10"
                        : "bg-slate-950/70 border-slate-800 text-slate-400 hover:bg-slate-900 hover:text-slate-200"
                    }`}
                  >
                    <FolderGit2 className={`w-3.5 h-3.5 ${isActive ? "text-indigo-400" : "text-slate-500"}`} />
                    <div>
                      <div className="font-semibold text-white truncate max-w-[200px]">
                        {run.run_name}
                      </div>
                      <div className="text-[10px] text-slate-400">
                        {run.transaction_count} items • {formatCurrency(run.total_spend, "INR")}
                      </div>
                    </div>

                    <button
                      onClick={(e) => handleDeleteRun(run.id, e)}
                      className="p-1 rounded hover:bg-rose-950/60 text-slate-500 hover:text-rose-400 transition-colors ml-1"
                      title="Delete this test scan result"
                    >
                      <X className="w-3 h-3" />
                    </button>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* Live Scanning Progress Banner */}
        {scanProgress && (scanProgress.is_scanning || scanProgress.stage === "extracting" || scanProgress.stage === "fetching") && (
          <div className="p-5 rounded-2xl bg-indigo-950/40 border border-indigo-800/60 shadow-lg shadow-indigo-950/20">
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center space-x-2">
                <div className="w-3 h-3 rounded-full bg-indigo-400 animate-ping" />
                <span className="font-semibold text-sm text-indigo-200">
                  Processing Inbox Receipts & Invoices
                </span>
              </div>
              <span className="text-xs text-indigo-300 font-mono">
                {scanProgress.scanned_count} / {scanProgress.total_count} emails
              </span>
            </div>
            <p className="text-xs text-slate-400 mb-3">{scanProgress.message}</p>
            <div className="w-full h-2 bg-slate-900 rounded-full overflow-hidden">
              <div 
                className="h-full bg-gradient-to-r from-indigo-500 to-violet-500 transition-all duration-300"
                style={{
                  width: `${scanProgress.total_count > 0 ? (scanProgress.scanned_count / scanProgress.total_count) * 100 : 15}%`
                }}
              />
            </div>
          </div>
        )}

        {/* Empty Inbox / Initial Scan CTA */}
        {data?.summary.transaction_count === 0 && !isScanning && (
          <div className="p-8 rounded-2xl bg-gradient-to-r from-indigo-950/60 to-slate-900 border border-indigo-800/50 text-center space-y-4 shadow-xl">
            <div className="w-12 h-12 rounded-2xl bg-indigo-600/20 border border-indigo-500/30 flex items-center justify-center mx-auto text-indigo-400">
              <Sparkles className="w-6 h-6" />
            </div>
            <h2 className="text-xl font-bold text-white">Your Gmail account is connected!</h2>
            <p className="text-sm text-slate-400 max-w-lg mx-auto">
              Click below to start an isolated inbox scan for receipts, Google Play game vouchers, Flipkart orders, and bills.
            </p>
            <div className="pt-2">
              <button
                onClick={triggerScan}
                className="px-6 py-3 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-semibold text-sm shadow-lg shadow-indigo-600/20 transition-all inline-flex items-center space-x-2 cursor-pointer"
              >
                <RefreshCw className="w-4 h-4" />
                <span>Start Scanning My Inbox</span>
              </button>
            </div>
          </div>
        )}

        {/* Top Summary Metric KPI Cards */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="p-5 rounded-2xl bg-slate-900/70 border border-slate-800/80 backdrop-blur-sm">
            <div className="flex items-center justify-between text-slate-400 mb-3">
              <span className="text-xs font-semibold uppercase tracking-wider">Total Tracked Spend</span>
              <DollarSign className="w-4 h-4 text-emerald-400" />
            </div>
            <div className="text-2xl sm:text-3xl font-extrabold text-white">
              {formatCurrency(totalSpend, currency)}
            </div>
            <div className="mt-2 text-xs text-slate-500 flex items-center space-x-1">
              <span>{data?.summary.transaction_count || 0} transactions in this run</span>
            </div>
          </div>

          <div className="p-5 rounded-2xl bg-slate-900/70 border border-slate-800/80 backdrop-blur-sm">
            <div className="flex items-center justify-between text-slate-400 mb-3">
              <span className="text-xs font-semibold uppercase tracking-wider">Top Spend Category</span>
              <TrendingUp className="w-4 h-4 text-blue-400" />
            </div>
            <div className="text-2xl sm:text-3xl font-extrabold text-white capitalize">
              {topCategory ? topCategory.category : "N/A"}
            </div>
            <div className="mt-2 text-xs text-slate-500">
              {topCategory ? `${formatCurrency(topCategory.total, currency)} (${topCategory.percentage}% of total)` : "No transactions"}
            </div>
          </div>

          <div className="p-5 rounded-2xl bg-slate-900/70 border border-slate-800/80 backdrop-blur-sm">
            <div className="flex items-center justify-between text-slate-400 mb-3">
              <span className="text-xs font-semibold uppercase tracking-wider">Top Merchant</span>
              <CreditCard className="w-4 h-4 text-violet-400" />
            </div>
            <div className="text-2xl sm:text-3xl font-extrabold text-white truncate">
              {topMerchant ? topMerchant.merchant : "N/A"}
            </div>
            <div className="mt-2 text-xs text-slate-500">
              {topMerchant ? `${formatCurrency(topMerchant.total, currency)} cumulative` : "No data"}
            </div>
          </div>

          <div className="p-5 rounded-2xl bg-slate-900/70 border border-amber-900/40 bg-amber-950/10 backdrop-blur-sm">
            <div className="flex items-center justify-between text-amber-400 mb-3">
              <span className="text-xs font-semibold uppercase tracking-wider">Flagged Insights</span>
              <AlertTriangle className="w-4 h-4 text-amber-400" />
            </div>
            <div className="text-2xl sm:text-3xl font-extrabold text-amber-200">
              {anomalyCount}
            </div>
            <div className="mt-2 text-xs text-amber-400/70">
              {anomalyCount > 0 ? "Price jumps & spending anomalies" : "All patterns normal"}
            </div>
          </div>
        </div>

        {/* Flagged Insights & Anomalies Section */}
        {data?.anomalies && data.anomalies.length > 0 && (
          <section className="space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-2">
                <Sparkles className="w-5 h-5 text-indigo-400" />
                <h2 className="text-lg font-bold text-white">AI Phrased Insights & Spending Anomalies</h2>
              </div>
              <span className="text-xs text-slate-500">
                Rule-computed facts • LLM natural language explanations
              </span>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {data.anomalies.map((anomaly) => {
                const isAlert = anomaly.severity === "alert";
                const isWarning = anomaly.severity === "warning";
                
                return (
                  <div
                    key={anomaly.id}
                    className={`p-5 rounded-2xl border transition-all ${
                      isAlert 
                        ? "bg-rose-950/20 border-rose-800/50 hover:border-rose-700" 
                        : isWarning 
                        ? "bg-amber-950/20 border-amber-800/50 hover:border-amber-700"
                        : "bg-slate-900/70 border-slate-800 hover:border-slate-700"
                    }`}
                  >
                    <div className="flex items-start justify-between gap-2 mb-3">
                      <div className="flex items-center space-x-2">
                        {isAlert && <Zap className="w-4 h-4 text-rose-400 shrink-0" />}
                        {isWarning && <AlertCircle className="w-4 h-4 text-amber-400 shrink-0" />}
                        {!isAlert && !isWarning && <Info className="w-4 h-4 text-indigo-400 shrink-0" />}
                        <span className={`text-xs font-bold uppercase tracking-wider ${
                          isAlert ? "text-rose-400" : isWarning ? "text-amber-400" : "text-indigo-400"
                        }`}>
                          {anomaly.flag_type.replace(/_/g, " ")}
                        </span>
                      </div>
                      
                      {anomaly.gmail_permalink && (
                        <a
                          href={anomaly.gmail_permalink}
                          target="_blank"
                          rel="noreferrer"
                          className="text-xs px-2 py-1 rounded-md bg-slate-800/90 hover:bg-slate-700 text-slate-300 font-medium flex items-center space-x-1 transition-colors shrink-0"
                          title="View source email in Gmail"
                        >
                          <span>View Email</span>
                          <ExternalLink className="w-3 h-3" />
                        </a>
                      )}
                    </div>

                    <h3 className="text-sm font-semibold text-white mb-2">
                      {anomaly.title}
                    </h3>

                    <p className="text-xs text-slate-300 leading-relaxed font-normal bg-slate-950/40 p-3 rounded-xl border border-slate-800/50">
                      &ldquo;{anomaly.explanation}&rdquo;
                    </p>
                  </div>
                );
              })}
            </div>
          </section>
        )}

        {/* Middle Section: Category Breakdown + Recurring Subscriptions */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
          
          {/* Category Breakdown (5 cols) */}
          <div className="lg:col-span-5 p-6 rounded-2xl bg-slate-900/70 border border-slate-800/80 flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center space-x-2">
                  <PieChart className="w-4 h-4 text-indigo-400" />
                  <h3 className="text-base font-bold text-white">Spend by Category</h3>
                </div>
                <span className="text-xs text-slate-500">{data?.summary.categories.length || 0} categories</span>
              </div>

              <div className="space-y-4">
                {data?.summary.categories.map((cat) => {
                  const style = CATEGORY_COLORS[cat.category.toLowerCase()] || CATEGORY_COLORS.other;
                  return (
                    <div key={cat.category} className="space-y-1.5">
                      <div className="flex items-center justify-between text-xs">
                        <span className="capitalize font-semibold text-slate-200 flex items-center space-x-1.5">
                          <span className={`w-2 h-2 rounded-full ${style.bar}`} />
                          <span>{cat.category}</span>
                        </span>
                        <div className="space-x-2">
                          <span className="text-slate-400 font-mono">{formatCurrency(cat.total, currency)}</span>
                          <span className="text-slate-500 font-semibold">({cat.percentage}%)</span>
                        </div>
                      </div>
                      <div className="w-full h-1.5 bg-slate-800 rounded-full overflow-hidden">
                        <div
                          className={`h-full ${style.bar} rounded-full transition-all duration-500`}
                          style={{ width: `${Math.min(cat.percentage, 100)}%` }}
                        />
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Monthly Trend Mini-bars */}
            {data?.summary.monthly_trends && data.summary.monthly_trends.length > 0 && (
              <div className="mt-8 pt-6 border-t border-slate-800">
                <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-3 flex items-center space-x-1.5">
                  <Calendar className="w-3.5 h-3.5 text-slate-400" />
                  <span>Monthly Spend History</span>
                </h4>
                <div className="grid grid-cols-3 gap-2">
                  {data.summary.monthly_trends.slice(-3).map((trend) => (
                    <div key={trend.month} className="p-2.5 rounded-xl bg-slate-950/60 border border-slate-800/80 text-center">
                      <span className="text-[10px] text-slate-500 block uppercase font-mono">{trend.month}</span>
                      <span className="text-xs font-bold text-slate-200 block mt-0.5">{formatCurrency(trend.total, currency)}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Recurring Subscriptions & Bills (7 cols) */}
          <div className="lg:col-span-7 p-6 rounded-2xl bg-slate-900/70 border border-slate-800/80">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center space-x-2">
                <Repeat className="w-4 h-4 text-purple-400" />
                <h3 className="text-base font-bold text-white">Recurring Subscriptions & Bills</h3>
              </div>
              <span className="text-xs text-slate-500">
                {data?.recurring_subscriptions.length || 0} active recurring streams
              </span>
            </div>

            {(!data?.recurring_subscriptions || data.recurring_subscriptions.length === 0) ? (
              <div className="py-12 text-center text-slate-500 text-xs">
                No recurring subscriptions detected in this scan run.
              </div>
            ) : (
              <div className="space-y-3 max-h-[380px] overflow-y-auto pr-1">
                {data.recurring_subscriptions.map((sub, idx) => (
                  <div
                    key={idx}
                    className="p-4 rounded-xl bg-slate-950/60 border border-slate-800/80 hover:border-slate-700 transition-colors flex items-center justify-between"
                  >
                    <div className="space-y-1">
                      <div className="flex items-center space-x-2">
                        <span className="font-semibold text-sm text-slate-100">{sub.merchant}</span>
                        <span className="text-[10px] px-2 py-0.5 rounded-full bg-purple-500/10 text-purple-400 border border-purple-500/20 font-medium capitalize">
                          {sub.cadence}
                        </span>
                      </div>
                      <div className="flex items-center space-x-3 text-xs text-slate-400">
                        <span>Seen {sub.frequency_count} times</span>
                        <span>•</span>
                        <span className="capitalize">{sub.category}</span>
                        <span>•</span>
                        <span>Latest: {sub.latest_date}</span>
                      </div>
                    </div>

                    <div className="flex items-center space-x-4">
                      <div className="text-right">
                        <div className="text-sm font-bold text-white font-mono">
                          {formatCurrency(sub.latest_amount, sub.currency)}
                        </div>
                        <div className="text-[10px] text-slate-500">
                          avg {formatCurrency(sub.average_amount, sub.currency)}
                        </div>
                      </div>

                      {sub.gmail_permalink && (
                        <a
                          href={sub.gmail_permalink}
                          target="_blank"
                          rel="noreferrer"
                          className="p-2 rounded-lg bg-slate-900 hover:bg-slate-800 text-slate-400 hover:text-slate-200 transition-colors"
                          title="View source email"
                        >
                          <ExternalLink className="w-4 h-4" />
                        </a>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Transactions Table Section */}
        <section className="p-6 rounded-2xl bg-slate-900/70 border border-slate-800/80 space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div className="flex items-center space-x-2">
              <Layers className="w-4 h-4 text-indigo-400" />
              <h3 className="text-base font-bold text-white">Extracted Financial Transactions</h3>
              <span className="text-xs px-2 py-0.5 rounded-full bg-slate-800 text-slate-400 font-mono">
                {filteredTransactions.length}
              </span>
            </div>

            {/* Filter and Search controls */}
            <div className="flex items-center gap-3">
              <div className="relative">
                <Search className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
                <input
                  type="text"
                  placeholder="Search merchant or subject..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="pl-8 pr-3 py-1.5 text-xs rounded-lg bg-slate-950 border border-slate-800 text-slate-200 placeholder:text-slate-500 focus:outline-none focus:border-indigo-500 w-48 sm:w-60"
                />
              </div>

              <select
                value={selectedCategory}
                onChange={(e) => setSelectedCategory(e.target.value)}
                className="px-3 py-1.5 text-xs rounded-lg bg-slate-950 border border-slate-800 text-slate-200 focus:outline-none focus:border-indigo-500 capitalize"
              >
                <option value="all">All Categories</option>
                {data?.summary.categories.map((c) => (
                  <option key={c.category} value={c.category}>
                    {c.category}
                  </option>
                ))}
              </select>
            </div>
          </div>

          {/* Table */}
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-950/60 text-slate-400 uppercase tracking-wider font-semibold border-b border-slate-800">
                <tr>
                  <th className="py-3 px-4">Date</th>
                  <th className="py-3 px-4">Merchant</th>
                  <th className="py-3 px-4">Category</th>
                  <th className="py-3 px-4">Type</th>
                  <th className="py-3 px-4">Subject & Email Snippet</th>
                  <th className="py-3 px-4 text-right">Amount</th>
                  <th className="py-3 px-4 text-center">Trace</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60">
                {filteredTransactions.length === 0 ? (
                  <tr>
                    <td colSpan={7} className="py-10 text-center text-slate-500">
                      No matching transactions found in this scan run.
                    </td>
                  </tr>
                ) : (
                  filteredTransactions.map((tx) => {
                    const catStyle = CATEGORY_COLORS[tx.category.toLowerCase()] || CATEGORY_COLORS.other;
                    return (
                      <tr key={tx.id} className="hover:bg-slate-800/30 transition-colors">
                        <td className="py-3 px-4 font-mono text-slate-400 whitespace-nowrap">
                          {tx.date}
                        </td>
                        <td className="py-3 px-4 font-semibold text-white whitespace-nowrap">
                          {tx.merchant}
                        </td>
                        <td className="py-3 px-4 whitespace-nowrap">
                          <span className={`px-2 py-0.5 rounded-full text-[10px] font-medium capitalize ${catStyle.bg} ${catStyle.text}`}>
                            {tx.category}
                          </span>
                        </td>
                        <td className="py-3 px-4 whitespace-nowrap">
                          <span className="text-[10px] text-slate-400 capitalize">
                            {tx.transaction_type.replace(/_/g, " ")}
                          </span>
                        </td>
                        <td className="py-3 px-4 max-w-xs sm:max-w-md truncate text-slate-400" title={tx.snippet || tx.subject}>
                          <span className="font-medium text-slate-300">{tx.subject}</span>
                          {tx.snippet && <span className="ml-1.5 text-slate-500 font-normal truncate">— {tx.snippet}</span>}
                        </td>
                        <td className="py-3 px-4 text-right font-bold text-slate-100 font-mono whitespace-nowrap">
                          {formatCurrency(tx.amount, tx.currency)}
                        </td>
                        <td className="py-3 px-4 text-center whitespace-nowrap">
                          {tx.gmail_permalink ? (
                            <a
                              href={tx.gmail_permalink}
                              target="_blank"
                              rel="noreferrer"
                              className="inline-flex items-center space-x-1 text-indigo-400 hover:text-indigo-300 bg-indigo-500/10 hover:bg-indigo-500/20 px-2 py-1 rounded-md text-[10px] font-medium transition-colors"
                              title="Open original email in Gmail"
                            >
                              <span>Gmail</span>
                              <ExternalLink className="w-2.5 h-2.5" />
                            </a>
                          ) : (
                            <span className="text-slate-600 text-[10px]">-</span>
                          )}
                        </td>
                      </tr>
                    );
                  })
                )}
              </tbody>
            </table>
          </div>
        </section>

      </main>

      {/* Real-World Privacy & Security Management Modal */}
      {showPrivacyModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-lg w-full p-6 space-y-5 shadow-2xl relative">
            <button
              onClick={() => setShowPrivacyModal(false)}
              className="absolute top-4 right-4 text-slate-400 hover:text-white p-1 rounded-lg hover:bg-slate-800"
            >
              <X className="w-5 h-5" />
            </button>

            <div className="flex items-center space-x-3">
              <div className="w-10 h-10 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 flex items-center justify-center">
                <ShieldCheck className="w-5 h-5" />
              </div>
              <div>
                <h3 className="font-bold text-base text-white">Privacy & Google Access Controls</h3>
                <p className="text-xs text-slate-400">Manage consent, active permissions, and data retention</p>
              </div>
            </div>

            <div className="p-3.5 rounded-xl bg-slate-950/60 border border-slate-800 space-y-2 text-xs">
              <div className="flex justify-between items-center text-slate-300">
                <span className="text-slate-400">Connected Account:</span>
                <span className="font-semibold text-white">{data?.user_email}</span>
              </div>
              <div className="flex justify-between items-center text-slate-300">
                <span className="text-slate-400">Google Scope:</span>
                <span className="font-mono text-emerald-400 bg-emerald-950/40 px-2 py-0.5 rounded text-[11px]">gmail.readonly</span>
              </div>
              <div className="flex justify-between items-center text-slate-300">
                <span className="text-slate-400">Raw Email Storage:</span>
                <span className="text-slate-300 font-medium">None (Only extracted numbers)</span>
              </div>
            </div>

            <div className="space-y-2.5 pt-2">
              <button
                onClick={handleRevokeGoogleAccess}
                disabled={isPurging}
                className="w-full py-2.5 px-4 rounded-xl bg-rose-950/50 border border-rose-800/60 hover:bg-rose-900/50 text-rose-200 font-semibold text-xs transition-colors flex items-center justify-center space-x-2 cursor-pointer disabled:opacity-50"
              >
                <Trash2 className="w-4 h-4 text-rose-400" />
                <span>Stop Sharing & Revoke Google Access</span>
              </button>
              <p className="text-[11px] text-slate-500 text-center">
                Formally revokes Google OAuth token and permanently deletes all local transactions.
              </p>
            </div>

            <div className="border-t border-slate-800 pt-4 flex items-center justify-between text-xs text-slate-400">
              <span>Verify in Google:</span>
              <a
                href="https://myaccount.google.com/connections"
                target="_blank"
                rel="noreferrer"
                className="text-indigo-400 hover:text-indigo-300 flex items-center space-x-1"
              >
                <span>Google Account Permissions</span>
                <ExternalLink className="w-3 h-3" />
              </a>
            </div>
          </div>
        </div>
      )}

      {/* Footer */}
      <footer className="border-t border-slate-900 py-6 px-4 text-center text-xs text-slate-400">
        <p>Gmail Spend Intelligence • Built for Polarisk Technical Assessment</p>
      </footer>
    </div>
  );
}
