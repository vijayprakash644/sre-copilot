# Build Progress

## Phase 1 — Core (Week 1) [ ]
- [x] Project scaffold + config
- [x] Scrubber (ai/scrubber.py) — MUST BE FIRST
- [x] Pydantic models
- [x] DB setup (aiosqlite)
- [x] PagerDuty webhook receiver + HMAC
- [x] AlertManager webhook receiver
- [x] LLM client factory (api|bedrock|ollama modes)
- [x] Claude triage call with XML output parsing
- [x] Health check endpoints
- [x] Basic test fixtures

## Phase 2 — RAG (Week 2) [ ]
- [x] ChromaDB setup + persistence
- [x] Document ingestion (PDF + Markdown)
- [x] Runbook search (semantic)
- [x] Past incident memory collection
- [x] Log fetching: Datadog integration
- [x] Log fetching: CloudWatch integration
- [x] Full triage pipeline (alert + logs + runbooks + past incidents)

## Phase 3 — Slack Bot (Week 3) [ ]
- [x] Slack Bolt app setup
- [x] Block Kit message formatter (severity badges, code blocks)
- [x] Feedback buttons (resolved, escalate, wrong diagnosis)
- [x] /sre-ask slash command (RAG follow-up in thread)
- [x] Feedback storage to DB

## Phase 4 — Production (Week 4) [ ]
- [x] Docker multi-stage build
- [x] Railway deploy config
- [x] Bedrock mode (AnthropicBedrock client swap)
- [x] Runbook upload API endpoint + auth
- [x] Alert history API
- [x] README + setup guide

## Phase 5 — Frontend [ ]
- [x] Next.js scaffold
- [x] Landing page (hero, how it works, pricing)
- [x] Dashboard: alert history table
- [x] Dashboard: runbook upload
- [x] Dashboard: alert detail with triage output
