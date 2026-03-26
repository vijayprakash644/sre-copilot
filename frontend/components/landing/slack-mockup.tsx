"use client";

import React from "react";
import { cn } from "@/lib/utils";
import {
  CheckCircle2,
  AlertTriangle,
  ChevronRight,
  ThumbsUp,
  ThumbsDown,
  Zap,
} from "lucide-react";

interface SlackMockupProps {
  className?: string;
}

export function SlackMockup({ className }: SlackMockupProps) {
  return (
    <div
      className={cn(
        "rounded-xl border border-white/10 bg-[#1a1d21] overflow-hidden shadow-2xl shadow-black/50",
        className
      )}
    >
      {/* Slack top bar */}
      <div className="flex items-center gap-2 px-4 py-3 bg-[#19171D] border-b border-white/10">
        <div className="flex gap-1.5">
          <div className="w-3 h-3 rounded-full bg-red-500/80" />
          <div className="w-3 h-3 rounded-full bg-yellow-500/80" />
          <div className="w-3 h-3 rounded-full bg-green-500/80" />
        </div>
        <div className="flex-1 flex items-center justify-center">
          <span className="text-xs text-gray-400 font-medium"># incidents-prod</span>
        </div>
      </div>

      {/* Alert trigger message */}
      <div className="px-4 py-4 border-b border-white/5">
        <div className="flex gap-3">
          <div className="w-9 h-9 rounded-lg bg-red-600 flex items-center justify-center flex-shrink-0 mt-0.5">
            <AlertTriangle className="w-5 h-5 text-white" />
          </div>
          <div className="flex-1 min-w-0">
            <div className="flex items-baseline gap-2 mb-1">
              <span className="text-sm font-bold text-white">PagerDuty</span>
              <span className="text-xs text-gray-500">Today at 3:07 AM</span>
            </div>
            <div className="rounded-md border-l-4 border-red-500 bg-red-950/30 px-3 py-2">
              <div className="flex items-center gap-2 mb-1">
                <span className="text-xs font-bold uppercase tracking-wider text-red-400 bg-red-500/20 px-2 py-0.5 rounded-full border border-red-500/30">
                  P1
                </span>
                <span className="text-sm font-semibold text-white">
                  Payment service — 503 errors spiking
                </span>
              </div>
              <p className="text-xs text-gray-400">
                Error rate: <span className="text-red-400 font-semibold">47%</span> &nbsp;·&nbsp;
                Affected: <span className="text-orange-400 font-semibold">checkout, billing</span>
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* SRE Copilot response */}
      <div className="px-4 py-4">
        <div className="flex gap-3">
          <div className="w-9 h-9 rounded-lg bg-gradient-to-br from-blue-600 to-violet-600 flex items-center justify-center flex-shrink-0 mt-0.5">
            <Zap className="w-4 h-4 text-white" />
          </div>
          <div className="flex-1 min-w-0">
            <div className="flex items-baseline gap-2 mb-2">
              <span className="text-sm font-bold text-white">SRE Copilot</span>
              <span className="text-xs text-gray-500">Today at 3:07 AM</span>
              <span className="text-xs text-blue-400 bg-blue-500/10 px-2 py-0.5 rounded-full border border-blue-500/20">
                9.2s
              </span>
            </div>

            {/* Diagnosis card */}
            <div className="rounded-lg border border-blue-500/20 bg-blue-950/20 p-3 mb-3">
              <div className="flex items-center gap-2 mb-2">
                <CheckCircle2 className="w-4 h-4 text-blue-400 flex-shrink-0" />
                <span className="text-sm font-semibold text-blue-300">
                  Root Cause Identified
                </span>
                <span className="ml-auto text-xs text-gray-400">
                  <span className="text-green-400 font-semibold">94%</span> confidence
                </span>
              </div>
              <p className="text-sm text-gray-300 leading-relaxed">
                Database connection pool exhausted on{" "}
                <code className="text-xs bg-white/10 px-1.5 py-0.5 rounded text-yellow-300">
                  payments-db-primary
                </code>
                . New deploy{" "}
                <code className="text-xs bg-white/10 px-1.5 py-0.5 rounded text-orange-300">
                  v2.14.3
                </code>{" "}
                at 2:51 AM increased connection hold time by 8×.
              </p>
            </div>

            {/* Action steps */}
            <div className="space-y-1.5 mb-3">
              <p className="text-xs font-semibold uppercase tracking-wider text-gray-500 mb-2">
                Recommended Actions
              </p>
              {[
                "Scale payments-db connection pool: max_connections 25 → 100",
                "Rollback v2.14.3 if step 1 does not resolve in 5 min",
                "Check runbook: payments-db-exhaustion.md §3.2",
              ].map((step, i) => (
                <div key={i} className="flex items-start gap-2">
                  <div className="w-5 h-5 rounded-full bg-white/10 flex items-center justify-center flex-shrink-0 mt-0.5">
                    <span className="text-xs text-gray-400 font-bold">{i + 1}</span>
                  </div>
                  <span className="text-xs text-gray-300 leading-relaxed">{step}</span>
                </div>
              ))}
            </div>

            {/* Action buttons */}
            <div className="flex flex-wrap gap-2">
              {[
                {
                  label: "View Full Diagnosis",
                  icon: <ChevronRight className="w-3 h-3" />,
                  style: "bg-blue-600 hover:bg-blue-500 text-white",
                },
                {
                  label: "Acknowledge",
                  icon: <CheckCircle2 className="w-3 h-3" />,
                  style: "bg-white/10 hover:bg-white/15 text-gray-300",
                },
                {
                  label: "👍 Helpful",
                  icon: <ThumbsUp className="w-3 h-3" />,
                  style: "bg-white/10 hover:bg-white/15 text-gray-300",
                },
                {
                  label: "👎 Incorrect",
                  icon: <ThumbsDown className="w-3 h-3" />,
                  style: "bg-white/10 hover:bg-white/15 text-gray-300",
                },
              ].map((btn, i) => (
                <button
                  key={i}
                  className={cn(
                    "flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-colors cursor-default",
                    btn.style
                  )}
                >
                  {btn.label}
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
