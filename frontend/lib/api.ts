// Typed API client for SRE Copilot backend

export type Severity = "P1" | "P2" | "P3" | "P4";

export interface Alert {
  id: string;
  alert_name: string;
  service: string;
  severity: Severity;
  status: "open" | "resolved" | "acknowledged";
  triggered_at: string;
  resolved_at?: string;
  diagnosis_preview?: string;
  raw_payload?: Record<string, unknown>;
}

export interface AlertDetail extends Alert {
  diagnosis: {
    root_cause: string;
    confidence: number;
    explanation: string;
    action_steps: string[];
    runbook_references: string[];
    time_to_diagnose_ms: number;
  };
  feedback?: {
    rating: number;
    comment?: string;
  };
}

export interface Stats {
  total_alerts: number;
  avg_time_to_diagnose_ms: number;
  mttr_reduction_pct: number;
  open_alerts: number;
  resolved_today: number;
  top_services: Array<{ service: string; count: number }>;
}

export interface Runbook {
  id: string;
  filename: string;
  service?: string;
  uploaded_at: string;
  chunk_count: number;
  size_bytes: number;
}

export interface UploadRunbookResponse {
  id: string;
  filename: string;
  chunk_count: number;
  message: string;
}

export interface FeedbackPayload {
  alert_id: string;
  rating: number;
  comment?: string;
}

const PROXY_BASE = "/api/proxy";

async function request<T>(
  path: string,
  options?: RequestInit
): Promise<T> {
  const url = `${PROXY_BASE}${path}`;
  const res = await fetch(url, {
    headers: {
      "Content-Type": "application/json",
      ...options?.headers,
    },
    ...options,
  });

  if (!res.ok) {
    const text = await res.text().catch(() => "Unknown error");
    throw new Error(`API error ${res.status}: ${text}`);
  }

  return res.json() as Promise<T>;
}

// ── Alerts ────────────────────────────────────────────────────────────────────

export async function getAlerts(params?: {
  limit?: number;
  offset?: number;
  severity?: Severity;
  status?: string;
  service?: string;
}): Promise<{ alerts: Alert[]; total: number }> {
  const qs = new URLSearchParams();
  if (params?.limit) qs.set("limit", String(params.limit));
  if (params?.offset) qs.set("offset", String(params.offset));
  if (params?.severity) qs.set("severity", params.severity);
  if (params?.status) qs.set("status", params.status);
  if (params?.service) qs.set("service", params.service);
  const query = qs.toString() ? `?${qs.toString()}` : "";
  return request<{ alerts: Alert[]; total: number }>(`/alerts${query}`);
}

export async function getAlert(id: string): Promise<AlertDetail> {
  return request<AlertDetail>(`/alerts/${id}`);
}

// ── Stats ─────────────────────────────────────────────────────────────────────

export async function getStats(): Promise<Stats> {
  return request<Stats>("/stats");
}

// ── Runbooks ──────────────────────────────────────────────────────────────────

export async function getRunbooks(): Promise<{ runbooks: Runbook[] }> {
  return request<{ runbooks: Runbook[] }>("/runbooks");
}

export async function uploadRunbook(
  file: File
): Promise<UploadRunbookResponse> {
  const formData = new FormData();
  formData.append("file", file);

  const res = await fetch(`${PROXY_BASE}/runbooks/upload`, {
    method: "POST",
    body: formData,
    // Do NOT set Content-Type — browser sets multipart boundary automatically
  });

  if (!res.ok) {
    const text = await res.text().catch(() => "Unknown error");
    throw new Error(`Upload failed ${res.status}: ${text}`);
  }

  return res.json() as Promise<UploadRunbookResponse>;
}

export async function deleteRunbook(id: string): Promise<void> {
  await request<void>(`/runbooks/${id}`, { method: "DELETE" });
}

// ── Feedback ──────────────────────────────────────────────────────────────────

export async function submitFeedback(
  alertId: string,
  rating: number,
  comment?: string
): Promise<void> {
  await request<void>("/feedback", {
    method: "POST",
    body: JSON.stringify({ alert_id: alertId, rating, comment } satisfies FeedbackPayload),
  });
}

// ── Settings ──────────────────────────────────────────────────────────────────

export interface AppSettings {
  deployment_mode: "api_only" | "slack_bot" | "slack_webhook" | "hybrid";
  webhook_url?: string;
  slack_channel?: string;
  slack_bot_token_set: boolean;
  api_key_set: boolean;
  version: string;
}

export async function getSettings(): Promise<AppSettings> {
  return request<AppSettings>("/settings");
}
