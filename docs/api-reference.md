# SRE Copilot — API Reference

Base URL: `https://your-app.example.com`

Interactive docs (development mode only): `GET /docs`

All request and response bodies are JSON. Timestamps are ISO 8601 UTC.

---

## Authentication

Two authentication mechanisms are used:

| Mechanism | Applies to |
|---|---|
| `X-API-Key: <API_SECRET_KEY>` header | `/api/runbooks/*` endpoints |
| `X-PagerDuty-Signature: v1=<hmac>` header | `POST /webhooks/pagerduty` |
| `Authorization: Bearer <PAGERDUTY_WEBHOOK_SECRET>` header | `POST /webhooks/alertmanager` |
| No auth | `GET /health`, `GET /ready`, `GET /api/alerts/*`, `POST /api/feedback` |

If `API_SECRET_KEY` is not set in the environment, runbook endpoint auth is skipped (development mode only — always set it in production).

---

## Webhook Endpoints

### `POST /webhooks/pagerduty`

Receives PagerDuty v3 webhook events. Only `incident.triggered` events trigger triage; `incident.acknowledged` and `incident.resolved` are accepted and ignored.

**Authentication:** `X-PagerDuty-Signature: v1=<hmac-sha256>` header. The HMAC is computed over the raw request body using `PAGERDUTY_WEBHOOK_SECRET`. If the secret is not configured, validation is skipped (development only).

**Request body (PagerDuty v3 format):**

```json
{
  "messages": [
    {
      "event": {
        "event_type": "incident.triggered",
        "data": {
          "id": "P1ABC123",
          "number": 42,
          "title": "HIGH CPU: api-server CPU usage at 95%",
          "description": "CPU sustained above 90% for 10 minutes.",
          "status": "triggered",
          "urgency": "high",
          "created_at": "2026-03-26T10:00:00Z",
          "service": {
            "name": "api-server"
          }
        }
      }
    }
  ]
}
```

**Response:**

```json
{ "status": "accepted" }
```

HTTP `200` is returned as soon as the webhook is validated and enqueued. Triage runs asynchronously in the background. HTTP `403` is returned if the HMAC signature is invalid.

Duplicate detection uses `pd:<incident_id>` as the deduplication key — repeated deliveries of the same `incident.triggered` event are silently ignored after the first.

---

### `POST /webhooks/alertmanager`

Receives Prometheus AlertManager v2 webhook payloads. Only `status: "firing"` alerts are processed.

**Authentication:** `Authorization: Bearer <PAGERDUTY_WEBHOOK_SECRET>` header (the same `PAGERDUTY_WEBHOOK_SECRET` env var is reused). If the secret is not configured, the Bearer check is skipped.

**Request body (AlertManager v2 format):**

```json
{
  "alerts": [
    {
      "status": "firing",
      "fingerprint": "abc123def456",
      "labels": {
        "alertname": "HighMemoryUsage",
        "service": "payment-service",
        "env": "production",
        "severity": "warning"
      },
      "annotations": {
        "summary": "Payment service memory usage above 90%",
        "description": "Heap usage at 92% for the last 5 minutes."
      },
      "startsAt": "2026-03-26T10:00:00Z"
    }
  ]
}
```

**Response:**

```json
{ "status": "accepted" }
```

Deduplication key: `am:<fingerprint>`. If `fingerprint` is absent, a SHA-256 hash of sorted labels is used.

---

### `POST /webhooks/datadog`

Receives Datadog monitor alert events. Only `metric_alert_monitor` and `service_check` event types are processed.

**Authentication:** None currently enforced (Datadog webhooks do not support HMAC out of the box). Restrict access at the network/firewall level.

**Request body (Datadog webhook format):**

```json
{
  "id": 123456789,
  "event_type": "metric_alert_monitor",
  "title": "CPU high on api-server",
  "body": "CPU usage exceeded 90% on api-server-prod-1",
  "tags": ["service:api-server", "env:production"],
  "url": "https://app.datadoghq.com/monitors/123456789"
}
```

**Response:**

```json
{ "status": "accepted" }
```

If `event_type` is not `metric_alert_monitor` or `service_check`, the response is `{"status": "ignored", "reason": "event_type=<type>"}`.

---

## Alert Endpoints

### `GET /api/alerts`

List recent alerts with their triage results, most recent first.

**Query parameters:**

| Parameter | Type | Default | Description |
|---|---|---|---|
| `limit` | integer | `50` | Number of results (1–200) |
| `offset` | integer | `0` | Pagination offset |

**Response:** Array of `AlertWithTriage` objects.

```json
[
  {
    "alert": {
      "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
      "source": "pagerduty",
      "name": "HIGH CPU: api-server CPU usage at 95%",
      "description": "CPU sustained above 90% for 10 minutes.",
      "service": "api-server",
      "environment": null,
      "labels": {
        "pagerduty_id": "P1ABC123",
        "urgency": "high",
        "status": "triggered"
      },
      "annotations": {},
      "fired_at": "2026-03-26T10:00:00Z",
      "raw_payload": {}
    },
    "triage": {
      "alert_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
      "severity": "P1",
      "diagnosis": "The api-server is CPU-saturated. Based on the 95% sustained utilisation over 10 minutes, this is likely caused by a traffic spike or a blocking operation in the request handlers.",
      "actions": [
        "`kubectl top pods -n production -l app=api-server`",
        "`kubectl scale deployment api-server -n production --replicas=6`",
        "Check recent deployments: `kubectl rollout history deployment/api-server -n production`"
      ],
      "escalate_to": "Platform team if CPU remains above 90% after scaling",
      "watch_out": "Rolling restart will cause ~30s of 503s — announce in #incidents first",
      "runbook_sources": ["runbook_chunk_1", "runbook_chunk_2"],
      "past_incident_refs": ["incident_1"],
      "llm_model": "claude-sonnet-4-6-20250514-1",
      "deployment_mode": "api",
      "created_at": "2026-03-26T10:00:08Z",
      "feedback": null
    }
  }
]
```

---

### `GET /api/alerts/{alert_id}`

Get a single alert with its triage result.

**Path parameter:** `alert_id` — UUID string.

**Response:** Single `AlertWithTriage` object (same shape as above).

**Error response:** HTTP `404` if the alert ID does not exist.

```json
{ "detail": "Alert not found" }
```

---

### `GET /api/alerts/stats`

Aggregate statistics for all alerts in the database.

**Response:**

```json
{
  "total_alerts": 142,
  "p1_count": 12,
  "p2_count": 48,
  "p3_count": 82,
  "feedback_good_rate": 0.87
}
```

`feedback_good_rate` is the fraction of alerts with explicit feedback where the rating was `"good"`. Alerts with no feedback are excluded from the rate calculation.

---

## Runbook Endpoints

All runbook endpoints require the `X-API-Key` header.

### `POST /api/runbooks/upload`

Upload a runbook file for indexing. The file is chunked, embedded with `voyage-3`, and stored in ChromaDB.

**Content type:** `multipart/form-data`

**Form field:** `file` — the runbook file (`.md` or `.pdf` only).

**Request example:**

```bash
curl -X POST https://your-app/api/runbooks/upload \
  -H "X-API-Key: $API_SECRET_KEY" \
  -F "file=@./runbooks/redis-out-of-memory.md"
```

**Response (HTTP 200):**

```json
{
  "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "filename": "redis-out-of-memory.md",
  "content_type": "markdown",
  "chunk_count": 4,
  "ingested_at": "2026-03-26T10:00:00Z"
}
```

**Error responses:**

| Status | Condition |
|---|---|
| `400` | File extension is not `.md` or `.pdf` |
| `401` | Missing or invalid `X-API-Key` |
| `500` | File parsing or ChromaDB ingestion failed |

---

### `GET /api/runbooks`

List all ingested runbook documents.

**Request example:**

```bash
curl -H "X-API-Key: $API_SECRET_KEY" https://your-app/api/runbooks
```

**Response:** Array of `RunbookDocument` objects.

```json
[
  {
    "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    "filename": "redis-out-of-memory.md",
    "content_type": "markdown",
    "chunk_count": 4,
    "ingested_at": "2026-03-26T10:00:00Z"
  },
  {
    "id": "7cb2a1e8-9f34-4b21-a5d6-1e8f9c2b3a4d",
    "filename": "kubernetes-crashloopbackoff.pdf",
    "content_type": "pdf",
    "chunk_count": 11,
    "ingested_at": "2026-03-25T14:30:00Z"
  }
]
```

---

### `DELETE /api/runbooks/{doc_id}`

Remove a runbook and all its embedded chunks from ChromaDB.

**Path parameter:** `doc_id` — UUID string from the upload response.

**Request example:**

```bash
curl -X DELETE \
  -H "X-API-Key: $API_SECRET_KEY" \
  https://your-app/api/runbooks/3fa85f64-5717-4562-b3fc-2c963f66afa6
```

**Response (HTTP 200):**

```json
{
  "status": "deleted",
  "doc_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6"
}
```

**Error responses:**

| Status | Condition |
|---|---|
| `401` | Missing or invalid `X-API-Key` |
| `404` | Runbook ID not found |

---

## Feedback Endpoint

### `POST /api/feedback`

Record thumbs-up or thumbs-down feedback on a triage result. This is called automatically by the Slack button handlers but can also be called directly.

**Request body:**

```json
{
  "alert_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "rating": "good"
}
```

| Field | Type | Values | Required |
|---|---|---|---|
| `alert_id` | string (UUID) | Any valid alert ID | Yes |
| `rating` | string | `"good"` or `"bad"` | Yes |
| `comment` | string | Free text | No |

**Response (HTTP 200):**

```json
{
  "status": "ok",
  "alert_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "rating": "good"
}
```

**Error responses:**

| Status | Condition |
|---|---|
| `404` | Alert ID not found |
| `422` | Invalid rating value (not `"good"` or `"bad"`) |

---

## Health Endpoints

### `GET /health`

Liveness probe. Returns immediately without checking dependencies. Use this for container health checks and load balancer pings.

**Response (HTTP 200):**

```json
{
  "status": "ok",
  "mode": "api"
}
```

`mode` reflects the current `DEPLOYMENT_MODE` value.

---

### `GET /ready`

Readiness probe. Checks the SQLite database connection and makes a minimal LLM API call (`Say 'ok'`, max 5 tokens). Returns HTTP `200` for both `"ok"` and `"degraded"` states — use the body to determine actual health.

**Response (HTTP 200, all healthy):**

```json
{
  "status": "ok",
  "db": "ok",
  "llm": "ok"
}
```

**Response (HTTP 200, degraded):**

```json
{
  "status": "degraded",
  "db": "ok",
  "llm": "unavailable"
}
```

If `llm` is `"unavailable"`, triage calls will fail. Check the deployment mode configuration, API keys, and network connectivity.

---

## Error Format

All error responses use this shape:

```json
{
  "detail": "Human-readable error message"
}
```

Unhandled server errors return:

```json
{
  "error": "Internal server error",
  "request_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

Include the `request_id` when reporting bugs or filing support tickets.
