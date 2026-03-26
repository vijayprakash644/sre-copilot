# SRE Copilot — Data Handling, Privacy & Security

This document describes exactly what data SRE Copilot processes, how sensitive information is removed before it leaves your system, and what guarantees each deployment mode provides.

---

## What Data Is Processed

When an alert fires, SRE Copilot processes the following data:

| Data type | Source | Stored in | Sent to LLM |
|---|---|---|---|
| Alert name, description, service, environment | Webhook payload | SQLite | Yes (after scrubbing) |
| Alert labels and annotations | Webhook payload | SQLite | Yes (after scrubbing) |
| Raw webhook payload | PagerDuty / AlertManager / Datadog | SQLite (scrubbed) | No |
| Log lines | Passed in triage call (optional) | Not stored | Yes (last 20 lines, after scrubbing) |
| Runbook text chunks | Uploaded by you | ChromaDB (scrubbed) | Yes (top 3 relevant chunks) |
| Past incident summaries | Generated from prior triage results | ChromaDB (scrubbed) | Yes (top 2 similar incidents) |
| LLM triage result | LLM response | SQLite | No |
| User feedback (good/bad) | Slack buttons / API | SQLite | No |

**Nothing is sent to any external service before being passed through the scrubber.** This is enforced at the code level: `ai/scrubber.py::get_scrubber()` is called on every external payload in `webhook/pagerduty.py`, `webhook/alertmanager.py`, `webhook/datadog_events.py`, and `ai/rag.py` before any data touches ChromaDB or the LLM.

---

## The Scrubber: Patterns Stripped From All Data

The scrubber (`backend/ai/scrubber.py`) applies 15 regex patterns in sequence before any data is stored or sent externally. Patterns are designed to be conservative — they prefer false positives (redacting too much) over false negatives.

| # | Pattern name | What is matched | Replacement |
|---|---|---|---|
| 1 | `email` | Email addresses (`user@example.com`) | `[REDACTED_EMAIL]` |
| 2 | `jwt` | JWT tokens (three base64url segments: `eyJ...eyJ...sig`) | `[REDACTED_JWT]` |
| 3 | `bearer_token` | `Authorization: Bearer <token>` header values | `Bearer [REDACTED_TOKEN]` |
| 4 | `slack_token` | Slack API tokens (`xoxb-`, `xoxp-`, `xoxa-`, `xoxs-`, `xapp-`) | `[REDACTED_SLACK_TOKEN]` |
| 5 | `aws_access_key` | AWS access key IDs (`AKIA...`, 20-char pattern) | `[REDACTED_AWS_KEY]` |
| 6 | `anthropic_key` | Anthropic API keys (`sk-ant-...`) | `[REDACTED_ANTHROPIC_KEY]` |
| 7 | `openai_key` | Generic `sk-` API keys (20+ chars) | `[REDACTED_API_KEY]` |
| 8 | `github_token` | GitHub tokens (`ghp_`, `gho_`, `github_pat_` prefixes) | `[REDACTED_GITHUB_TOKEN]` |
| 9 | `password_kv` | Key=value or key: value pairs where the key is `password`, `passwd`, `secret`, `api_key`, `apikey`, `token`, `credential`, or `auth` | `[REDACTED_CREDENTIAL]=` / `[REDACTED]` |
| 10 | `db_connection_string` | Database URLs with embedded credentials (`postgres://user:pass@host/db`, `mysql://`, `mongodb://`, `redis://`, `amqp://`) | `[REDACTED_CONNECTION_STRING]` |
| 11 | `private_ip_10` | RFC 1918 private IPs in the `10.x.x.x` range | `[REDACTED_PRIVATE_IP]` |
| 12 | `private_ip_172` | RFC 1918 private IPs in the `172.16.x.x`–`172.31.x.x` range | `[REDACTED_PRIVATE_IP]` |
| 13 | `private_ip_192` | RFC 1918 private IPs in the `192.168.x.x` range | `[REDACTED_PRIVATE_IP]` |
| 14 | `public_ip` | Public IPv4 addresses (heuristic; excludes `0.x`, `127.x`, `255.x`) | `[REDACTED_IP]` |
| 15 | `credit_card` | Credit card numbers (Visa, Mastercard, Amex, Discover, JCB patterns) | `[REDACTED_CARD]` |

### Adding Custom Patterns

Customer-specific patterns (e.g., internal user IDs, customer account numbers) can be added at runtime without code changes:

```python
from ai.scrubber import get_scrubber

scrubber = get_scrubber()
scrubber.add_pattern(
    name="internal_user_id",
    pattern=r"USR-[0-9]{8}",
    replacement="[REDACTED_USER_ID]",
)
```

### Verifying Scrubber Output

To verify what the scrubber strips from a specific string:

```python
from ai.scrubber import LogScrubber

s = LogScrubber()
print(s.scrub("user=admin password=secret123 ip=10.0.0.1"))
# Output: user=admin [REDACTED_CREDENTIAL]=[REDACTED] ip=[REDACTED_PRIVATE_IP]
```

---

## Deployment Mode 1: Anthropic API (`DEPLOYMENT_MODE=api`)

**Data flow:** Scrubbed alert data → HTTPS → Anthropic's API servers → response returned

- Uses the `anthropic` Python SDK over TLS.
- Default model: `claude-sonnet-4-6-20250514-1`.
- Anthropic's standard API policy retains inputs for up to 7 days for abuse monitoring.
- If your Anthropic account has **Zero Data Retention (ZDR)** enabled, inputs are not stored beyond the duration of the API call.
- Data is processed in Anthropic's US data centres (us-east-1 region) by default.
- Anthropic does not use API inputs to train models.

**Best for:** Teams that want the simplest setup and are comfortable with Anthropic's data handling policy.

---

## Deployment Mode 2: AWS Bedrock (`DEPLOYMENT_MODE=bedrock`, `AWS_REGION=us-east-1`)

**Data flow:** Scrubbed alert data → AWS Bedrock API (in your AWS account) → response returned

- Uses `anthropic.AnthropicBedrock` which routes through AWS Bedrock's API endpoint.
- All inference happens inside your AWS account. No data is sent to Anthropic's servers.
- AWS Bedrock does not use your inputs to train foundation models.
- Data is subject to your AWS account's security controls (IAM, VPC endpoints, CloudTrail).
- You can restrict network access to Bedrock via VPC endpoints (`com.amazonaws.<region>.bedrock-runtime`).
- Credentials can be supplied via environment variables (`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`) or via an IAM instance/task role (preferred — no credentials in env).

**Best for:** Enterprises with existing AWS infrastructure and strict data residency requirements.

---

## Deployment Mode 3: Self-Hosted Ollama (`DEPLOYMENT_MODE=ollama`)

**Data flow:** Scrubbed alert data → local Ollama HTTP API → response returned

- All inference runs on your own hardware. No data leaves your network.
- Compatible with any model served by Ollama (default: `llama3.1:8b`).
- Embeddings still use the Anthropic `voyage-3` API if `ANTHROPIC_API_KEY` is set. To make embeddings fully local too, leave `ANTHROPIC_API_KEY` unset — the system falls back to a deterministic hash-based stub embedding (reduced RAG quality, but fully air-gapped).
- No API keys required.

**Best for:** Air-gapped environments, regulated industries, or teams that cannot send any data externally.

---

## Deployment Mode 4: AWS Bedrock in Tokyo (`DEPLOYMENT_MODE=bedrock`, `AWS_REGION=ap-northeast-1`)

**Data flow:** Scrubbed alert data → AWS Bedrock API in Tokyo region → response returned

- Identical to Mode 2, but all data at rest and in transit stays within Japan's `ap-northeast-1` region.
- Ensures compliance with Japan's **Act on the Protection of Personal Information (APPI)**, which requires personal data to be processed within Japan or in countries with equivalent protections, or with the explicit consent of data subjects.
- Verify that the `anthropic.claude-sonnet-4-6-20250514-v1:0` model is available in `ap-northeast-1` in your AWS account (Bedrock model availability varies by region — request access in the AWS console under **Bedrock → Model access**).

---

## Zero Data Retention (ZDR)

For the highest level of data protection using Anthropic's API (Mode 1):

1. Contact [Anthropic's sales team](https://www.anthropic.com/contact-sales) to enable Zero Data Retention on your account.
2. With ZDR enabled, Anthropic does not store prompt or completion data beyond the duration of the API call.
3. ZDR applies to `claude-sonnet-4-6-20250514-1` and other Claude models on the API.
4. Note: ZDR is a contractual agreement with Anthropic and is not verified by SRE Copilot itself.

For guaranteed zero external retention without relying on contractual agreements, use Mode 2 (Bedrock) or Mode 3 (Ollama).

---

## APPI Compliance Notes for Japanese Customers

The **Act on the Protection of Personal Information (APPI)** governs the handling of personal information in Japan. Key considerations for SRE Copilot deployments:

1. **Use Deployment Mode 4** (Bedrock, `ap-northeast-1`) to ensure all data processing occurs within Japan.

2. **The scrubber removes email addresses and IPs** which may constitute personal information under APPI. However, alert payloads may contain other personal data depending on your systems (e.g., usernames in log lines). Review your alert payloads and add custom scrubbing patterns for any personally-identifying fields.

3. **Runbooks should not contain personal data.** Before uploading runbooks, verify they do not reference specific individuals' contact details, internal account IDs linked to natural persons, or other personal information as defined under APPI.

4. **Data stored in ChromaDB** (runbook chunks, past incident summaries) and SQLite (alert history, triage results) resides on the host where SRE Copilot is deployed. For APPI compliance, this host must be within Japan or in a jurisdiction with equivalent protections. AWS Tokyo (`ap-northeast-1`) satisfies this when using ECS/EC2 with EBS volumes in that region.

5. **Consult your Data Protection Officer** before deploying SRE Copilot in environments where alert data may routinely contain personal information as defined under APPI Article 2.

---

## Network Security

- The FastAPI backend listens on port 8000. In production, all traffic should be routed through a TLS-terminating reverse proxy (see `infra/nginx/`).
- Webhook endpoints (`/webhooks/*`) are publicly reachable but protected by HMAC validation (PagerDuty) or Bearer token (AlertManager).
- Admin endpoints (`/api/runbooks/*`) are protected by the `X-API-Key` header matching `API_SECRET_KEY`.
- The `/docs` Swagger UI is disabled when `APP_ENV=production`.
- CORS is restricted to origins listed in `ALLOWED_ORIGINS`.
- The application runs as a non-root user (`appuser`, UID 1000) inside the Docker container.
