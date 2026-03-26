"use client";

import React from "react";
import {
  CheckCircle2,
  AlertTriangle,
  Clock,
  BookOpen,
  Zap,
  ChevronRight,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import type { AlertDetail } from "@/lib/api";
import { cn } from "@/lib/utils";

interface TriageCardProps {
  alert: AlertDetail;
  onViewDetail?: () => void;
  className?: string;
}

export function TriageCard({ alert, onViewDetail, className }: TriageCardProps) {
  const d = alert.diagnosis;
  if (!d) return null;

  const confidenceColor =
    d.confidence >= 80
      ? "text-green-400"
      : d.confidence >= 60
      ? "text-yellow-400"
      : "text-red-400";

  const confidenceBg =
    d.confidence >= 80
      ? "from-green-600/20 to-emerald-600/20 border-green-500/20"
      : d.confidence >= 60
      ? "from-yellow-600/20 to-orange-600/20 border-yellow-500/20"
      : "from-red-600/20 to-rose-600/20 border-red-500/20";

  return (
    <Card
      className={cn(
        "bg-[#0d0f14] border-white/10 text-white overflow-hidden",
        className
      )}
    >
      {/* Top accent bar based on severity */}
      <div
        className={cn(
          "h-1 w-full",
          alert.severity === "P1"
            ? "bg-gradient-to-r from-red-600 to-rose-600"
            : alert.severity === "P2"
            ? "bg-gradient-to-r from-orange-500 to-amber-500"
            : alert.severity === "P3"
            ? "bg-gradient-to-r from-yellow-500 to-amber-400"
            : "bg-gradient-to-r from-blue-500 to-cyan-500"
        )}
      />

      <CardHeader className="pb-3">
        <div className="flex items-start justify-between gap-3">
          <div className="flex items-start gap-2 min-w-0">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-blue-600/20 to-violet-600/20 flex items-center justify-center flex-shrink-0 mt-0.5">
              <Zap className="w-4 h-4 text-blue-400" />
            </div>
            <div className="min-w-0">
              <p className="text-sm font-semibold text-white leading-snug truncate">
                {alert.alert_name}
              </p>
              <p className="text-xs text-gray-500 mt-0.5">{alert.service}</p>
            </div>
          </div>
          <Badge
            variant={
              alert.severity === "P1"
                ? "p1"
                : alert.severity === "P2"
                ? "p2"
                : alert.severity === "P3"
                ? "p3"
                : "p4"
            }
            className="flex-shrink-0"
          >
            {alert.severity}
          </Badge>
        </div>
      </CardHeader>

      <CardContent className="space-y-4">
        {/* Confidence indicator */}
        <div
          className={cn(
            "rounded-lg border bg-gradient-to-br p-3",
            confidenceBg
          )}
        >
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4 text-blue-400" />
              <span className="text-xs font-semibold text-gray-300">Root Cause</span>
            </div>
            <span className={cn("text-sm font-bold", confidenceColor)}>
              {d.confidence}% confidence
            </span>
          </div>
          <p className="text-sm text-white font-medium leading-snug">
            {d.root_cause}
          </p>
        </div>

        {/* Top action step */}
        {d.action_steps.length > 0 && (
          <div>
            <p className="text-xs text-gray-500 mb-2 flex items-center gap-1.5">
              <AlertTriangle className="w-3 h-3" />
              Immediate action
            </p>
            <div className="flex items-start gap-2 rounded-lg bg-white/[0.03] border border-white/5 px-3 py-2">
              <span className="w-5 h-5 rounded-full bg-orange-500/20 flex items-center justify-center flex-shrink-0 text-xs text-orange-400 font-bold mt-0.5">
                1
              </span>
              <p className="text-sm text-gray-300 leading-relaxed">
                {d.action_steps[0]}
              </p>
            </div>
            {d.action_steps.length > 1 && (
              <p className="text-xs text-gray-600 mt-1 pl-7">
                +{d.action_steps.length - 1} more steps
              </p>
            )}
          </div>
        )}

        {/* Meta row */}
        <div className="flex items-center gap-4 text-xs text-gray-500 pt-1">
          <span className="flex items-center gap-1.5">
            <Clock className="w-3 h-3" />
            {(d.time_to_diagnose_ms / 1000).toFixed(1)}s diagnosis
          </span>
          {d.runbook_references.length > 0 && (
            <span className="flex items-center gap-1.5">
              <BookOpen className="w-3 h-3" />
              {d.runbook_references.length} runbook{d.runbook_references.length !== 1 ? "s" : ""} cited
            </span>
          )}
        </div>

        {onViewDetail && (
          <Button
            variant="ghost"
            size="sm"
            className="w-full justify-between text-gray-400 hover:text-white hover:bg-white/5 border border-white/5"
            onClick={onViewDetail}
          >
            View full diagnosis
            <ChevronRight className="w-4 h-4" />
          </Button>
        )}
      </CardContent>
    </Card>
  );
}
