# Project Structure

```
sre-copilot/
├── CLAUDE.md                        # Claude Code memory (this project)
├── PROJECT_STRUCTURE.md             # This file
├── PROGRESS.md                      # Build progress tracker
├── README.md                        # User-facing setup guide
│
├── backend/                         # Python FastAPI application
│   ├── main.py                      # App entry point, router registration
│   ├── config.py                    # Settings (pydantic-settings + .env)
│   ├── models.py                    # Pydantic models: Alert, TriageResult, etc.
│   ├── db.py                        # aiosqlite setup, CRUD helpers
│   │
│   ├── ai/
│   │   ├── __init__.py
│   │   ├── client.py                # LLM client factory (api|bedrock|ollama)
│   │   ├── prompts.py               # System prompt + user message template
│   │   ├── triage.py                # triage_alert() — main orchestration
│   │   ├── rag.py                   # ChromaDB ingest + search_runbooks()
│   │   ├── scrubber.py              # Log/data scrubber (runs FIRST always)
│   │   └── embeddings.py            # Embedding helpers
│   │
│   ├── webhook/
│   │   ├── __init__.py
│   │   ├── router.py                # FastAPI router, mounts all sources
│   │   ├── pagerduty.py             # PagerDuty v3 webhook + HMAC validation
│   │   ├── alertmanager.py          # Prometheus AlertManager webhook
│   │   └── datadog_events.py        # Optional: Datadog event webhook
│   │
│   ├── integrations/
│   │   ├── __init__.py
│   │   ├── slack.py                 # Slack Bolt app, message formatter
│   │   ├── datadog.py               # Datadog Logs API client
│   │   ├── cloudwatch.py            # AWS CloudWatch Logs client
│   │   └── loki.py                  # Grafana Loki client (optional)
│   │
│   ├── api/
│   │   ├── __init__.py
│   │   ├── runbooks.py              # POST /runbooks/upload, GET /runbooks
│   │   ├── alerts.py                # GET /alerts, GET /alerts/{id}
│   │   ├── feedback.py              # POST /feedback (thumbs up/down)
│   │   └── health.py                # GET /health, GET /ready
│   │
│   └── tests/
│       ├── conftest.py
│       ├── fixtures/
│       │   ├── sample_pd_alert.json
│       │   ├── sample_am_alert.json
│       │   └── sample_logs.txt
│       ├── test_scrubber.py
│       ├── test_triage.py
│       ├── test_webhooks.py
│       └── test_rag.py
│
├── frontend/                        # Next.js marketing + dashboard
│   ├── app/
│   │   ├── layout.tsx
│   │   ├── page.tsx                 # Marketing landing page
│   │   ├── pricing/page.tsx
│   │   ├── docs/page.tsx
│   │   ├── dashboard/
│   │   │   ├── layout.tsx
│   │   │   ├── page.tsx             # Alert history dashboard
│   │   │   ├── runbooks/page.tsx    # Runbook management
│   │   │   └── settings/page.tsx   # Workspace settings
│   │   └── api/
│   │       └── proxy/route.ts       # API proxy to backend
│   ├── components/
│   │   ├── ui/                      # shadcn/ui components
│   │   ├── layout/
│   │   │   ├── navbar.tsx
│   │   │   └── footer.tsx
│   │   ├── landing/
│   │   │   ├── hero.tsx
│   │   │   ├── how-it-works.tsx
│   │   │   ├── pricing.tsx
│   │   │   └── social-proof.tsx
│   │   └── dashboard/
│   │       ├── alert-table.tsx
│   │       ├── alert-detail.tsx
│   │       ├── runbook-upload.tsx
│   │       └── triage-card.tsx
│   ├── lib/
│   │   ├── api.ts                   # Backend API client
│   │   └── utils.ts
│   └── public/
│
├── infra/
│   ├── Dockerfile                   # Multi-stage production build
│   ├── docker-compose.yml           # Local dev with all services
│   ├── docker-compose.prod.yml      # Production compose reference
│   ├── railway.toml                 # Railway deployment config
│   ├── terraform/
│   │   ├── bedrock-mode/            # Terraform for customer AWS deploy
│   │   │   ├── main.tf
│   │   │   ├── iam.tf
│   │   │   └── variables.tf
│   │   └── railway-mode/
│   │       └── README.md
│   └── nginx/
│       └── nginx.conf               # Reverse proxy config
│
├── scripts/
│   ├── seed_runbooks.py             # Ingest sample runbooks into ChromaDB
│   ├── test_alert.sh                # Fire test alerts at local server
│   └── setup_slack.sh               # Slack app setup helper
│
├── docs/
│   ├── setup-guide.md               # Customer 5-step setup
│   ├── deployment-modes.md          # The 4 deployment modes explained
│   ├── privacy-security.md          # Data handling, scrubber, APPI info
│   ├── runbook-format.md            # How to write runbooks for best results
│   └── api-reference.md             # Webhook + REST API docs
│
├── .env.example                     # All required env vars documented
├── .gitignore
├── pyproject.toml                   # Python deps via uv
└── pnpm-workspace.yaml              # Monorepo pnpm config
```
