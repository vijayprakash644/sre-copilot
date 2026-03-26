"use client";

import React, { useEffect, useState } from "react";
import {
  Bell,
  TrendingDown,
  Clock,
  CheckCircle2,
  Loader2,
  AlertTriangle,
} from "lucide-react";
import { AlertTable } from "@/components/dashboard/alert-table";
import { AlertDetail } from "@/components/dashboard/alert-detail";
import { getStats, type Stats } from "@/lib/api";

function StatCard({
  icon,
  label,
  value,
  sub,
  loading,
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
  sub?: string;
  loading?: boolean;
}) {
  return (
    <div className="rounded-xl border border-white/10 bg-white/[0.02] p-5 flex items-start gap-4">
      <div className="w-10 h-10 rounded-lg bg-white/5 flex items-center justify-center flex-shrink-0">
        {icon}
      </div>
      <div className="min-w-0">
        <p className="text-xs text-gray-500 mb-1">{label}</p>
        {loading ? (
          <div className="h-7 w-24 bg-white/5 rounded animate-pulse" />
        ) : (
          <p className="text-2xl font-bold text-white">{value}</p>
        )}
        {sub && <p className="text-xs text-gray-600 mt-0.5">{sub}</p>}
      </div>
    </div>
  );
}

export default function DashboardPage() {
  const [stats, setStats] = useState<Stats | null>(null);
  const [statsLoading, setStatsLoading] = useState(true);
  const [selectedAlertId, setSelectedAlertId] = useState<string | null>(null);
  const [detailOpen, setDetailOpen] = useState(false);

  useEffect(() => {
    setStatsLoading(true);
    getStats()
      .then(setStats)
      .catch(() => {})
      .finally(() => setStatsLoading(false));
  }, []);

  function handleSelectAlert(id: string) {
    setSelectedAlertId(id);
    setDetailOpen(true);
  }

  return (
    <div className="p-6 space-y-6 max-w-7xl mx-auto">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-white">Alert History</h1>
        <p className="text-sm text-gray-500 mt-1">
          Browse all incidents and their AI-generated diagnoses.
        </p>
      </div>

      {/* Stats bar */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          icon={<Bell className="w-5 h-5 text-red-400" />}
          label="Open alerts"
          value={stats?.open_alerts != null ? String(stats.open_alerts) : "—"}
          loading={statsLoading}
        />
        <StatCard
          icon={<CheckCircle2 className="w-5 h-5 text-green-400" />}
          label="Resolved today"
          value={stats?.resolved_today != null ? String(stats.resolved_today) : "—"}
          loading={statsLoading}
        />
        <StatCard
          icon={<Clock className="w-5 h-5 text-blue-400" />}
          label="Avg. diagnosis time"
          value={
            stats?.avg_time_to_diagnose_ms != null
              ? `${(stats.avg_time_to_diagnose_ms / 1000).toFixed(1)}s`
              : "—"
          }
          sub="target < 10s"
          loading={statsLoading}
        />
        <StatCard
          icon={<TrendingDown className="w-5 h-5 text-violet-400" />}
          label="MTTR reduction"
          value={
            stats?.mttr_reduction_pct != null
              ? `${stats.mttr_reduction_pct}%`
              : "—"
          }
          sub="vs. pre-deployment baseline"
          loading={statsLoading}
        />
      </div>

      {/* Alert table */}
      <AlertTable onSelectAlert={handleSelectAlert} />

      {/* Detail side sheet */}
      <AlertDetail
        alertId={selectedAlertId}
        open={detailOpen}
        onOpenChange={setDetailOpen}
      />
    </div>
  );
}
