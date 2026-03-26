# SRE Copilot — Project Memory for Claude Code

## What this product is
SRE Copilot is a production AI incident triage tool. When a PagerDuty or AlertManager alert fires,
it automatically fetches logs, retrieves relevant runbooks via RAG, checks past incident memory,
and delivers a Claude-powered diagnosis + ordered action steps to Slack in under 10 seconds.

## Core value proposition
- Alert fires at 3am → engineer reads one Slack message → runs 2 commands → back to sleep
- MTTR reduction from ~45 min to ~4 min for common incidents
- Gets smarter over time by learning from your specific runbooks and past incidents

## Privacy architecture (critical — never compromise on this)
- ALL log lines pass through the scrubber BEFORE any processing or transmission
- Scrubber strips: emails, JWTs, passwords, credentials, private IPs, API keys, card numbers
- Four deployment modes: (1) Anthropic API + scrubber, (2) AWS Bedrock in customer VPC,
  (3) self-hosted Ollama, (4) AWS Bedrock ap-northeast-1 for Japan/APPI compliance
- Bedrock mode: data never leaves customer's AWS account

## Tech stack (never deviate without good reason)
- Backend: Python 3.11, FastAPI, async everywhere
- AI: Anthropic SDK (claude-sonnet-4-6), AnthropicBedrock for Mode 2/4
- Vector DB: ChromaDB (local persistent), swap to Pinecone at enterprise scale
- Embeddings: Anthropic embeddings (voyage-3 via Anthropic API)
- Slack: slack-bolt Python SDK, async mode
- Storage: aiosqlite for alert history (Postgres at scale)
- Deploy: Docker multi-stage, Railway for SaaS, customer AWS for Bedrock mode
- Frontend/website: Next.js 14 App Router, TypeScript, Tailwind CSS, shadcn/ui
- Package manager: uv (Python), pnpm (Node)

## Key design decisions
- XML tags in Claude prompts for reliable structured output parsing
- Scrubber runs on-process before anything, including ChromaDB storage
- Deployment mode selected via DEPLOYMENT_MODE env var (api|bedrock|ollama)
- All async — no blocking calls anywhere in the hot path
- Webhook HMAC validation on all inbound sources (PagerDuty, AlertManager)
- Log context: last 20 lines after scrubbing, capped at 4000 tokens total prompt

## File structure reference
See PROJECT_STRUCTURE.md for full layout.

## Environment reference
See .env.example for all required variables.

## Current build status
Track completed features in PROGRESS.md.
