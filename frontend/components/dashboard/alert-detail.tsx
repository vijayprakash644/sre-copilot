"use client";

import React, { useEffect, useState } from "react";
import {
  CheckCircle2,
  Clock,
  AlertTriangle,
  BookOpen,
  ThumbsUp,
  ThumbsDown,
  Loader2,
  ExternalLink,
} from "lucide-react";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetDescription,
} from "@/components/ui/sheet";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { getAlert, submitFeedback, type AlertDetail as AlertDetailType, type Severity } from "@/lib/api";
import { cn, formatDateTime, severityColor } from "@/lib/utils";

function severityVariant(s: Severity) {
  switch (s) {
    case "P1": return "p1";
    case "P2": return "p2";
    case "P3": return "p3";
    case "P4": return "p4";
    default: return "default" as const;
  }
}

interface AlertDetailProps {
  alertId: string | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function AlertDetail({ alertId, open, onOpenChange }: AlertDetailProps) {
  const [detail, setDetail] = useState<AlertDetailType | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [feedbackSent, setFeedbackSent] = useState<"helpful" | "incorrect" | null>(null);
  const [submittingFeedback, setSubmittingFeedback] = useState(false);

  useEffect(() => {
    if (!alertId || !open) return;
    setLoading(true);
    setError(null);
    setDetail(null);
    setFeedbackSent(null);

    getAlert(alertId)
      .then(setDetail)
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false));
  }, [alertId, open]);

  async function handleFeedback(rating: number, type: "helpful" | "incorrect") {
    if (!alertId || feedbackSent) return;
    setSubmittingFeedback(true);
    try {
      await submitFeedback(alertId, rating);
      setFeedbackSent(type);
    } catch {
      // silently fail feedback
    } finally {
      setSubmittingFeedback(false);
    }
  }

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent
        side="right"
        className="bg-[#0d0f14] border-white/10 text-white w-full sm:max-w-2xl overflow-y-auto"
      >
        {loading && (
          <div className="flex items-center justify-center h-64">
            <Loader2 className="w-8 h-8 text-blue-400 animate-spin" />
          </div>
        )}

        {error && (
          <div className="flex items-center justify-center h-64">
            <div className="text-center">
              <AlertTriangle className="w-10 h-10 text-red-400 mx-auto mb-3" />
              <p className="text-sm text-gray-400">{error}</p>
              <Button
                variant="outline"
                size="sm"
                className="mt-4 border-white/10"
                onClick={() => alertId && getAlert(alertId).then(setDetail).catch((e: Error) => setError(e.message))}
              >
                Retry
              </Button>
            </div>
          </div>
        )}

        {detail && (
          <>
            <SheetHeader className="mb-6 pr-8">
              <div className="flex items-start gap-3">
                <Badge variant={severityVariant(detail.severity)} className="mt-0.5 flex-shrink-0">
                  {detail.severity}
                </Badge>
                <div className="min-w-0">
                  <SheetTitle className="text-white text-lg leading-tight mb-1">
                    {detail.alert_name}
                  </SheetTitle>
                  <SheetDescription className="text-gray-400 text-sm">
                    {detail.service} &middot; {formatDateTime(detail.triggered_at)}
                  </SheetDescription>
                </div>
              </div>
            </SheetHeader>

            {/* Status row */}
            <div className="flex items-center gap-3 mb-6 flex-wrap">
              <span
                className={cn(
                  "inline-flex items-center gap-1.5 text-xs px-2.5 py-1 rounded-full border",
                  detail.status === "resolved"
                    ? "text-green-400 bg-green-500/10 border-green-500/20"
                    : detail.status === "acknowledged"
                    ? "text-blue-400 bg-blue-500/10 border-blue-500/20"
                    : "text-red-400 bg-red-500/10 border-red-500/20"
                )}
              >
                <span
                  className={cn(
                    "w-1.5 h-1.5 rounded-full",
                    detail.status === "resolved"
                      ? "bg-green-400"
                      : detail.status === "acknowledged"
                      ? "bg-blue-400"
                      : "bg-red-400 animate-pulse"
                  )}
                />
                {detail.status.charAt(0).toUpperCase() + detail.status.slice(1)}
              </span>

              {detail.diagnosis && (
                <span className="inline-flex items-center gap-1.5 text-xs px-2.5 py-1 rounded-full border border-white/10 text-gray-400">
                  <Clock className="w-3 h-3" />
                  Diagnosed in {(detail.diagnosis.time_to_diagnose_ms / 1000).toFixed(1)}s
                </span>
              )}
            </div>

            {/* Diagnosis */}
            {detail.diagnosis && (
              <div className="space-y-5">
                {/* Root cause */}
                <div className="rounded-xl border border-blue-500/20 bg-blue-950/20 p-4">
                  <div className="flex items-center gap-2 mb-3">
                    <CheckCircle2 className="w-4 h-4 text-blue-400 flex-shrink-0" />
                    <span className="text-sm font-semibold text-blue-300">Root Cause</span>
                    <div className="ml-auto flex items-center gap-1.5">
                      <span className="text-xs text-gray-500">Confidence</span>
                      <span
                        className={cn(
                          "text-xs font-bold",
                          detail.diagnosis.confidence >= 80
                            ? "text-green-400"
                            : detail.diagnosis.confidence >= 60
                            ? "text-yellow-400"
                            : "text-red-400"
                        )}
                      >
                        {detail.diagnosis.confidence}%
                      </span>
                    </div>
                  </div>
                  <p className="text-sm font-semibold text-white mb-2">
                    {detail.diagnosis.root_cause}
                  </p>
                  <p className="text-sm text-gray-400 leading-relaxed">
                    {detail.diagnosis.explanation}
                  </p>
                </div>

                {/* Action steps */}
                <div>
                  <h4 className="text-xs font-semibold uppercase tracking-wider text-gray-500 mb-3">
                    Recommended Actions
                  </h4>
                  <ol className="space-y-2">
                    {detail.diagnosis.action_steps.map((step, i) => (
                      <li key={i} className="flex items-start gap-3">
                        <span className="w-6 h-6 rounded-full bg-white/10 flex items-center justify-center flex-shrink-0 text-xs text-gray-400 font-bold mt-0.5">
                          {i + 1}
                        </span>
                        <span className="text-sm text-gray-300 leading-relaxed">{step}</span>
                      </li>
                    ))}
                  </ol>
                </div>

                {/* Runbook references */}
                {detail.diagnosis.runbook_references.length > 0 && (
                  <div>
                    <h4 className="text-xs font-semibold uppercase tracking-wider text-gray-500 mb-3">
                      Runbook References
                    </h4>
                    <ul className="space-y-2">
                      {detail.diagnosis.runbook_references.map((ref, i) => (
                        <li
                          key={i}
                          className="flex items-center gap-2 text-sm text-blue-400 hover:text-blue-300 transition-colors"
                        >
                          <BookOpen className="w-3.5 h-3.5 flex-shrink-0" />
                          <span className="font-mono text-xs">{ref}</span>
                          <ExternalLink className="w-3 h-3 ml-auto" />
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                {/* Feedback */}
                <div className="rounded-xl border border-white/10 bg-white/[0.02] p-4">
                  <p className="text-xs text-gray-500 mb-3">Was this diagnosis helpful?</p>
                  {feedbackSent ? (
                    <p className="text-sm text-green-400 flex items-center gap-2">
                      <CheckCircle2 className="w-4 h-4" />
                      Thanks for your feedback!
                    </p>
                  ) : (
                    <div className="flex gap-2">
                      <Button
                        variant="outline"
                        size="sm"
                        className="border-white/10 gap-2 hover:border-green-500/30 hover:text-green-400"
                        onClick={() => handleFeedback(5, "helpful")}
                        disabled={submittingFeedback}
                      >
                        {submittingFeedback ? (
                          <Loader2 className="w-3.5 h-3.5 animate-spin" />
                        ) : (
                          <ThumbsUp className="w-3.5 h-3.5" />
                        )}
                        Helpful
                      </Button>
                      <Button
                        variant="outline"
                        size="sm"
                        className="border-white/10 gap-2 hover:border-red-500/30 hover:text-red-400"
                        onClick={() => handleFeedback(1, "incorrect")}
                        disabled={submittingFeedback}
                      >
                        {submittingFeedback ? (
                          <Loader2 className="w-3.5 h-3.5 animate-spin" />
                        ) : (
                          <ThumbsDown className="w-3.5 h-3.5" />
                        )}
                        Incorrect
                      </Button>
                    </div>
                  )}
                </div>
              </div>
            )}

            {!detail.diagnosis && (
              <div className="rounded-xl border border-white/10 bg-white/[0.02] p-8 text-center">
                <AlertTriangle className="w-8 h-8 text-gray-600 mx-auto mb-3" />
                <p className="text-sm text-gray-400">No diagnosis available for this alert.</p>
              </div>
            )}
          </>
        )}
      </SheetContent>
    </Sheet>
  );
}
