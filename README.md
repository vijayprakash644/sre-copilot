# SRE Copilot

SRE Copilot is an AI-powered incident triage tool that connects to your alerting pipeline (PagerDuty, Prometheus AlertManager, or Datadog) and automatically posts a structured diagnosis and step-by-step resolution guide to Slack in under 10 seconds — without a human touching a keyboard. Every alert payload is scrubbed of secrets and PII before leaving your system, and you choose where the AI runs: Anthropic's API, AWS Bedrock inside your own account, or a self-hosted Ollama instance with no external calls at all.

---

## Architecture

```
                       ┌─────────────────────────────────────────────────┐
                       │               SRE Copilot                       │
                       │                                                 │
 AlertManager  ──────► │  POST /webhooks/alertmanager                   │
 PagerDuty     ──────► │  POST /webhooks/pagerduty    ┌──────────────┐  │
 Datadog       ──────► │  POST /webhooks/datadog      │   Scrubber   │  │
                       │         │                    │  (regex PII  │  │
                       │         ▼                    │   removal)   │  │
                       │  ┌─────────────┐             └──────┬───────┘  │
                       │  │  FastAPI    │◄───────────────────┘          │
                       │  │  Backend   │                                 │
                       │  └─────┬──────┘                                │
                       │        │                                        │
                       │   ┌────▼──────────────────────────────────┐    │
                       │   │   RAG Engine (ChromaDB)               │    │
                       │   │   - Runbook chunks (voyage-3 embeds)  │    │
                       │   │   - Past incident summaries           │    │
                       │   └────┬──────────────────────────────────┘    │
                       │        │ context                               │
                       │        ▼                                        │
                       │   ┌─────────────────────────────┐              │
                       │   │       LLM (mode-select)     │              │
                       │   │  api     → Anthropic API    │              │
                       │   │  bedrock → AWS Bedrock      │              │
                       │   │  ollama  → Local Ollama     │              │
                       │   └─────────────────────────────┘              │
                       │        │ XML triage result                     │
                       └────────┼────────────────────────────────────────┘
                                │
                                ▼
                          ┌──────────┐
                          │  Slack   │  Block Kit message with severity,
                          │  #incidents  diagnosis, actions, buttons
                          └──────────┘
```

---

## Quick Start

```bash
# 1. Clone and enter the project
git clone https://github.com/your-org/sre-copilot.git && cd sre-copilot

# 2. Copy the example env file and fill in your keys
cp .env.example .env

# 3. Build and start with Docker Compose
docker compose -f infra/docker-compose.yml up --build -d

# 4. Upload your first runbook
curl -X POST http://localhost:8000/api/runbooks/upload \
  -H "X-API-Key: $API_SECRET_KEY" \
  -F "file=@runbooks/my-service.md"

# 5. Fire a test alert and watch Slack
./scripts/test_alert.sh p1
```

---

## Environment Variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `DEPLOYMENT_MODE` | No | `api` | One of: `api`, `bedrock`, `ollama` |
| `ANTHROPIC_API_KEY` | Mode: `api` | — | Anthropic API key (`sk-ant-...`) |
| `ANTHROPIC_MODEL` | No | `claude-sonnet-4-6-20250514-1` | Model for `api` mode |
| `AWS_REGION` | Mode: `bedrock` | `us-east-1` | AWS region for Bedrock |
| `AWS_ACCESS_KEY_ID` | Mode: `bedrock`* | — | AWS key (omit if using instance role) |
| `AWS_SECRET_ACCESS_KEY` | Mode: `bedrock`* | — | AWS secret (omit if using instance role) |
| `AWS_SESSION_TOKEN` | No | — | AWS session token for temporary credentials |
| `BEDROCK_MODEL` | No | `anthropic.claude-sonnet-4-6-20250514-v1:0` | Bedrock model ID |
| `OLLAMA_BASE_URL` | Mode: `ollama` | `http://localhost:11434` | Ollama server URL |
| `OLLAMA_MODEL` | No | `llama3.1:8b` | Ollama model name |
| `SLACK_BOT_TOKEN` | No | — | Slack bot token (`xoxb-...`). Slack posts skipped if unset. |
| `SLACK_SIGNING_SECRET` | No | — | Slack signing secret for request verification |
| `INCIDENTS_CHANNEL` | No | `#incidents` | Slack channel to post triage messages |
| `PAGERDUTY_WEBHOOK_SECRET` | No | — | HMAC secret for PagerDuty webhook validation |
| `API_SECRET_KEY` | No | — | Protects `/api/runbooks/*` and related admin endpoints |
| `APP_ENV` | No | `development` | Set to `production` to enable JSON logging and disable /docs |
| `LOG_LEVEL` | No | `INFO` | Logging level |
| `DATABASE_URL` | No | `./data/sre_copilot.db` | SQLite database path |
| `CHROMA_PERSIST_DIR` | No | `./data/chroma` | ChromaDB persistence directory |
| `TRIAGE_TIMEOUT_SECONDS` | No | `15` | Hard timeout for LLM triage calls |
| `MAX_LOG_LINES` | No | `20` | Max log lines sent to LLM per alert |
| `MAX_RUNBOOK_CHUNKS` | No | `3` | Max runbook chunks retrieved per alert |

---

## Deployment Modes

SRE Copilot supports four deployment configurations selected via `DEPLOYMENT_MODE`.

### Mode 1: `api` — Anthropic API (default)
Uses the Anthropic API directly. Simplest setup. Alert data leaves your network to Anthropic's servers and is subject to their 7-day zero-data-retention policy (if ZDR is enabled on your account).

```env
DEPLOYMENT_MODE=api
ANTHROPIC_API_KEY=sk-ant-...
```

### Mode 2: `bedrock` — AWS Bedrock (us-east-1 or custom region)
Inference runs inside your AWS account via AWS Bedrock. No data leaves your AWS environment.

```env
DEPLOYMENT_MODE=bedrock
AWS_REGION=us-east-1
BEDROCK_MODEL=anthropic.claude-sonnet-4-6-20250514-v1:0
# AWS credentials via env vars or IAM instance role
```

### Mode 3: `ollama` — Self-Hosted (air-gapped)
Fully local inference. No external API calls. Requires an Ollama server with a loaded model.

```env
DEPLOYMENT_MODE=ollama
OLLAMA_BASE_URL=http://your-ollama-server:11434
OLLAMA_MODEL=llama3.1:8b
```

### Mode 4: Bedrock in `ap-northeast-1` — APPI Compliance (Japan)
Same as Bedrock mode, but with the region set to Tokyo to keep data within Japan. Required for APPI compliance.

```env
DEPLOYMENT_MODE=bedrock
AWS_REGION=ap-northeast-1
BEDROCK_MODEL=anthropic.claude-sonnet-4-6-20250514-v1:0
```

See [docs/deployment-modes.md](docs/deployment-modes.md) for full setup instructions per mode.

---

## Connecting PagerDuty

1. In PagerDuty, go to **Integrations → Generic Webhooks (v3)**.
2. Create a new webhook with URL: `https://your-app.example.com/webhooks/pagerduty`
3. Subscribe to the `incident.triggered` event type.
4. Copy the generated **HMAC secret** and set it as `PAGERDUTY_WEBHOOK_SECRET` in your `.env`.

SRE Copilot validates the `X-PagerDuty-Signature: v1=<hmac>` header on every request. If `PAGERDUTY_WEBHOOK_SECRET` is not set, HMAC validation is skipped (development only — always set it in production).

---

## Connecting Prometheus AlertManager

Add a webhook receiver to your `alertmanager.yml`:

```yaml
receivers:
  - name: sre-copilot
    webhook_configs:
      - url: https://your-app.example.com/webhooks/alertmanager
        http_config:
          authorization:
            credentials: "<your-PAGERDUTY_WEBHOOK_SECRET-value>"
        send_resolved: false
```

SRE Copilot processes only `status: firing` alerts and deduplicates by fingerprint.

---

## Uploading Runbooks

Runbooks are chunked, embedded with `voyage-3`, and stored in ChromaDB. The top-3 matching chunks are included in every triage prompt.

```bash
# Upload a Markdown runbook
curl -X POST https://your-app/api/runbooks/upload \
  -H "X-API-Key: $API_SECRET_KEY" \
  -F "file=@./runbooks/redis-oom.md"

# Upload a PDF runbook
curl -X POST https://your-app/api/runbooks/upload \
  -H "X-API-Key: $API_SECRET_KEY" \
  -F "file=@./runbooks/k8s-crashloop.pdf"

# List all runbooks
curl -H "X-API-Key: $API_SECRET_KEY" https://your-app/api/runbooks

# Delete a runbook
curl -X DELETE -H "X-API-Key: $API_SECRET_KEY" https://your-app/api/runbooks/<doc_id>
```

Supported formats: `.md` and `.pdf`. See [docs/runbook-format.md](docs/runbook-format.md) for best practices.

---

## Slack Bot

Every triage result is posted to `INCIDENTS_CHANNEL` as a Block Kit message containing:

- **Severity badge** (P1/P2/P3/UNKNOWN) with colour-coded emoji
- **Diagnosis** — 2-3 sentence plain-language explanation of the probable root cause
- **Immediate Actions** — numbered, copy-pasteable steps (shell commands are formatted as code)
- **Watch out / Escalate to** — optional callouts from the LLM
- **Context footer** — runbook sources, similar past incidents, fired timestamp

Each message has four interactive buttons:

| Button | Action |
|---|---|
| **Resolved** | Records `good` feedback and posts a thread confirmation |
| **Escalate** | Posts an escalation notice in the thread |
| **Wrong diagnosis** | Records `bad` feedback for future model improvement |
| **Ask follow-up** | Opens a modal to ask the AI a follow-up question about the incident |

**Slash command:** `/sre-ask <question>` — asks SRE Copilot an ad-hoc question with runbook context in any channel where the bot is present.

To set up the Slack app, run: `./scripts/setup_slack.sh` — it prints the full app manifest and step-by-step instructions.

---

## Contributing

1. Fork the repository and create a feature branch.
2. Run tests: `pytest backend/tests/`
3. The backend is a single FastAPI application in `backend/`. All configuration is in `backend/config.py`. New webhook sources go in `backend/webhook/`, new API endpoints in `backend/api/`.
4. The scrubber in `backend/ai/scrubber.py` must be applied to all external data before it touches ChromaDB or the LLM. Never bypass it.
5. Open a PR with a description of what you changed and why.
