"use client";

import React, { useEffect, useState, useCallback } from "react";
import {
  RefreshCw,
  AlertTriangle,
  Search,
  Filter,
  ChevronRight,
  Loader2,
} from "lucide-react";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { getAlerts, type Alert, type Severity } from "@/lib/api";
import { cn, formatRelativeTime, severityDot } from "@/lib/utils";

type SeverityVariant = "p1" | "p2" | "p3" | "p4" | "default";

function severityBadgeVariant(s: Severity): SeverityVariant {
  switch (s) {
    case "P1": return "p1";
    case "P2": return "p2";
    case "P3": return "p3";
    case "P4": return "p4";
    default: return "default";
  }
}

function statusBadge(status: Alert["status"]) {
  switch (status) {
    case "open":
      return (
        <span className="inline-flex items-center gap-1.5 text-xs text-red-400">
          <span className="w-1.5 h-1.5 rounded-full bg-red-400 animate-pulse" />
          Open
        </span>
      );
    case "acknowledged":
      return (
        <span className="inline-flex items-center gap-1.5 text-xs text-blue-400">
          <span className="w-1.5 h-1.5 rounded-full bg-blue-400" />
          Acknowledged
        </span>
      );
    case "resolved":
      return (
        <span className="inline-flex items-center gap-1.5 text-xs text-green-400">
          <span className="w-1.5 h-1.5 rounded-full bg-green-400" />
          Resolved
        </span>
      );
  }
}

// Skeleton rows for loading state
function SkeletonRow() {
  return (
    <TableRow className="border-white/5">
      {[1, 2, 3, 4, 5].map((i) => (
        <TableCell key={i} className="py-4">
          <div className="h-4 bg-white/5 rounded animate-pulse" style={{ width: `${60 + i * 10}%` }} />
        </TableCell>
      ))}
    </TableRow>
  );
}

interface AlertTableProps {
  onSelectAlert: (id: string) => void;
}

export function AlertTable({ onSelectAlert }: AlertTableProps) {
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [severityFilter, setSeverityFilter] = useState<Severity | "">("");
  const [page, setPage] = useState(0);
  const PAGE_SIZE = 20;

  const fetchAlerts = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await getAlerts({
        limit: PAGE_SIZE,
        offset: page * PAGE_SIZE,
        severity: severityFilter || undefined,
      });
      setAlerts(result.alerts);
      setTotal(result.total);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }, [page, severityFilter]);

  useEffect(() => {
    fetchAlerts();
  }, [fetchAlerts]);

  // Client-side search filter on loaded results
  const filtered = search.trim()
    ? alerts.filter(
        (a) =>
          a.alert_name.toLowerCase().includes(search.toLowerCase()) ||
          a.service.toLowerCase().includes(search.toLowerCase())
      )
    : alerts;

  const severities: Array<Severity | ""> = ["", "P1", "P2", "P3", "P4"];

  return (
    <div className="flex flex-col gap-4">
      {/* Toolbar */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center gap-3">
        {/* Search */}
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
          <input
            type="text"
            placeholder="Search alerts or services..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-9 pr-4 py-2 rounded-lg border border-white/10 bg-white/[0.03] text-sm text-white placeholder-gray-500 focus:outline-none focus:border-blue-500/50 focus:bg-white/[0.05] transition-colors"
          />
        </div>

        {/* Severity filter */}
        <div className="flex items-center gap-2">
          <Filter className="w-4 h-4 text-gray-500" />
          <div className="flex gap-1">
            {severities.map((s) => (
              <button
                key={s}
                onClick={() => {
                  setSeverityFilter(s);
                  setPage(0);
                }}
                className={cn(
                  "text-xs px-3 py-1.5 rounded-lg border transition-all",
                  severityFilter === s
                    ? s === ""
                      ? "border-white/30 bg-white/10 text-white"
                      : s === "P1"
                      ? "border-red-500/50 bg-red-500/20 text-red-400"
                      : s === "P2"
                      ? "border-orange-500/50 bg-orange-500/20 text-orange-400"
                      : s === "P3"
                      ? "border-yellow-500/50 bg-yellow-500/20 text-yellow-400"
                      : "border-blue-500/50 bg-blue-500/20 text-blue-400"
                    : "border-white/10 text-gray-500 hover:border-white/20 hover:text-gray-300"
                )}
              >
                {s === "" ? "All" : s}
              </button>
            ))}
          </div>
        </div>

        {/* Refresh */}
        <Button
          variant="ghost"
          size="icon"
          onClick={fetchAlerts}
          disabled={loading}
          className="text-gray-500 hover:text-white ml-auto"
          aria-label="Refresh alerts"
        >
          <RefreshCw className={cn("w-4 h-4", loading && "animate-spin")} />
        </Button>
      </div>

      {/* Table */}
      <div className="rounded-xl border border-white/10 overflow-hidden">
        <Table>
          <TableHeader>
            <TableRow className="border-white/10 hover:bg-transparent">
              <TableHead className="text-gray-500 w-20">Severity</TableHead>
              <TableHead className="text-gray-500">Alert</TableHead>
              <TableHead className="text-gray-500 hidden sm:table-cell">Service</TableHead>
              <TableHead className="text-gray-500 hidden md:table-cell">Status</TableHead>
              <TableHead className="text-gray-500 hidden lg:table-cell">When</TableHead>
              <TableHead className="text-gray-500">Diagnosis preview</TableHead>
              <TableHead className="w-8" />
            </TableRow>
          </TableHeader>
          <TableBody>
            {loading && !alerts.length && (
              <>
                <SkeletonRow />
                <SkeletonRow />
                <SkeletonRow />
                <SkeletonRow />
                <SkeletonRow />
              </>
            )}

            {!loading && error && (
              <TableRow className="border-white/5">
                <TableCell colSpan={7} className="py-16 text-center">
                  <AlertTriangle className="w-8 h-8 text-red-400 mx-auto mb-3" />
                  <p className="text-sm text-gray-400 mb-3">{error}</p>
                  <Button
                    variant="outline"
                    size="sm"
                    className="border-white/10"
                    onClick={fetchAlerts}
                  >
                    Retry
                  </Button>
                </TableCell>
              </TableRow>
            )}

            {!loading && !error && filtered.length === 0 && (
              <TableRow className="border-white/5">
                <TableCell colSpan={7} className="py-16 text-center">
                  <p className="text-sm text-gray-500">
                    {search ? "No alerts match your search." : "No alerts found."}
                  </p>
                </TableCell>
              </TableRow>
            )}

            {filtered.map((alert) => (
              <TableRow
                key={alert.id}
                className="border-white/5 cursor-pointer hover:bg-white/[0.03] transition-colors group"
                onClick={() => onSelectAlert(alert.id)}
              >
                <TableCell className="py-3">
                  <div className="flex items-center gap-2">
                    <span className={cn("w-2 h-2 rounded-full flex-shrink-0", severityDot(alert.severity))} />
                    <Badge variant={severityBadgeVariant(alert.severity)}>
                      {alert.severity}
                    </Badge>
                  </div>
                </TableCell>
                <TableCell className="py-3">
                  <span className="text-sm text-white font-medium leading-snug line-clamp-1">
                    {alert.alert_name}
                  </span>
                </TableCell>
                <TableCell className="py-3 hidden sm:table-cell">
                  <code className="text-xs text-gray-400 bg-white/5 px-2 py-0.5 rounded">
                    {alert.service}
                  </code>
                </TableCell>
                <TableCell className="py-3 hidden md:table-cell">
                  {statusBadge(alert.status)}
                </TableCell>
                <TableCell className="py-3 hidden lg:table-cell">
                  <span className="text-xs text-gray-500">
                    {formatRelativeTime(alert.triggered_at)}
                  </span>
                </TableCell>
                <TableCell className="py-3 max-w-xs">
                  <p className="text-xs text-gray-500 truncate">
                    {alert.diagnosis_preview ?? "—"}
                  </p>
                </TableCell>
                <TableCell className="py-3">
                  <ChevronRight className="w-4 h-4 text-gray-700 group-hover:text-gray-400 transition-colors" />
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>

      {/* Pagination */}
      {total > PAGE_SIZE && (
        <div className="flex items-center justify-between text-sm text-gray-500">
          <span>
            Showing {page * PAGE_SIZE + 1}–{Math.min((page + 1) * PAGE_SIZE, total)} of {total}
          </span>
          <div className="flex gap-2">
            <Button
              variant="outline"
              size="sm"
              className="border-white/10 disabled:opacity-30"
              onClick={() => setPage((p) => Math.max(0, p - 1))}
              disabled={page === 0 || loading}
            >
              Previous
            </Button>
            <Button
              variant="outline"
              size="sm"
              className="border-white/10 disabled:opacity-30"
              onClick={() => setPage((p) => p + 1)}
              disabled={(page + 1) * PAGE_SIZE >= total || loading}
            >
              Next
            </Button>
          </div>
        </div>
      )}

      {loading && alerts.length > 0 && (
        <div className="flex items-center justify-center py-2 text-xs text-gray-500 gap-2">
          <Loader2 className="w-3 h-3 animate-spin" />
          Refreshing...
        </div>
      )}
    </div>
  );
}
