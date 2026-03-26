# SRE Copilot — Setup Guide

This guide takes you from zero to a working SRE Copilot installation that receives alerts and posts AI triage results to Slack. Estimated time: 20 minutes.

---

## Step 1: Deploy SRE Copilot

### Option A — Railway (one-click, recommended for first deploy)

1. Click the **Deploy on Railway** button in the repository.
2. Railway reads `infra/railway.toml` and builds from `infra/Dockerfile` automatically.
3. After deploy, open **Variables** in the Railway dashboard and set the environment variables listed in Step 1b below.
4. Railway provides a public HTTPS URL like `https://sre-copilot-production.up.railway.app`. Copy it — you need it for Steps 2 and 3.

### Option B — Docker (self-hosted)

```bash
# Clone the repo
git clone https://github.com/your-org/sre-copilot.git
cd sre-copilot

# Create your .env file
cp .env.example .env
# Edit .env — minimum required variables listed below

# Start the stack (API + Redis)
docker compose -f infra/docker-compose.yml up -d

# For production with Nginx TLS termination:
docker compose -f infra/docker-compose.yml -f infra/docker-compose.prod.yml up -d
```

The API is available at `http://localhost:8000`. Health check: `curl http://localhost:8000/health`.

### Minimum required `.env` for first boot

```env
# Choose one deployment mode (see docs/deployment-modes.md for full options)
DEPLOYMENT_MODE=api
ANTHROPIC_API_KEY=sk-ant-...

# Slack (configure in Step 2)
SLACK_BOT_TOKEN=xoxb-...
SLACK_SIGNING_SECRET=...
INCIDENTS_CHANNEL=#incidents

# Admin API key for runbook management
API_SECRET_KEY=<generate with: openssl rand -hex 32>

# PagerDuty HMAC secret (configure in Step 3)
PAGERDUTY_WEBHOOK_SECRET=...
```

---

## Step 2: Create the Slack App and Install It

SRE Copilot uses Slack's Block Kit to post formatted triage messages and handles interactive buttons via Slack's Events API.

1. Run the setup helper to get the app manifest:

   ```bash
   SRE_COPILOT_URL=https://your-deployment-url ./scripts/setup_slack.sh
   ```

2. Go to [https://api.slack.com/apps](https://api.slack.com/apps) → **Create New App** → **From manifest**.

3. Paste the manifest printed by the script above. It configures:
   - Bot scopes: `chat:write`, `chat:write.public`, `commands`, `channels:read`, `channels:history`
   - Slash command: `/sre-ask` pointing to `https://your-app/slack/events`
   - Interactivity request URL: `https://your-app/slack/events`

4. Click **Install to Workspace** and authorize the permissions.

5. Copy the credentials into your `.env`:
   - **Bot Token** (`xoxb-...`) → `SLACK_BOT_TOKEN`
   - **Signing Secret** → `SLACK_SIGNING_SECRET`

6. Restart SRE Copilot if running locally so it picks up the new credentials.

> If you change the deployment URL later, update the Request URL under **Interactivity & Shortcuts** in the Slack app settings.

---

## Step 3: Connect PagerDuty

SRE Copilot validates all incoming PagerDuty webhooks using HMAC-SHA256. Always configure the secret in production.

1. In PagerDuty, navigate to **Integrations → Generic Webhooks (v3)** (or from a specific service: **Service Settings → Integrations → Add Webhook**).

2. Set the webhook URL to:

   ```
   https://your-app.example.com/webhooks/pagerduty
   ```

3. Subscribe to event type: **`incident.triggered`**. (SRE Copilot ignores `acknowledged` and `resolved` events automatically.)

4. PagerDuty will display a **webhook secret** after creation. Copy it and set it in your `.env`:

   ```env
   PAGERDUTY_WEBHOOK_SECRET=<paste secret here>
   ```

5. Restart SRE Copilot (or redeploy on Railway) to activate signature validation.

**Connecting Prometheus AlertManager instead:**

Add a webhook receiver to `alertmanager.yml`:

```yaml
receivers:
  - name: sre-copilot
    webhook_configs:
      - url: https://your-app.example.com/webhooks/alertmanager
        http_config:
          authorization:
            credentials: "your-PAGERDUTY_WEBHOOK_SECRET-value"
        send_resolved: false

route:
  receiver: sre-copilot
  group_wait: 30s
  group_interval: 5m
```

**Connecting Datadog instead:**

In Datadog, go to **Integrations → Webhooks** and create a webhook pointing to:

```
https://your-app.example.com/webhooks/datadog
```

SRE Copilot processes `metric_alert_monitor` and `service_check` events from Datadog.

---

## Step 4: Upload Your First Runbook

Runbooks are indexed with semantic embeddings and the top matching chunks are injected into every triage prompt. The more specific your runbooks, the more specific the triage output.

```bash
# Upload a Markdown runbook
curl -X POST https://your-app.example.com/api/runbooks/upload \
  -H "X-API-Key: $API_SECRET_KEY" \
  -F "file=@./runbooks/redis-out-of-memory.md"

# Upload a PDF runbook
curl -X POST https://your-app.example.com/api/runbooks/upload \
  -H "X-API-Key: $API_SECRET_KEY" \
  -F "file=@./runbooks/kubernetes-crashloopbackoff.pdf"
```

A successful upload returns:

```json
{
  "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "filename": "redis-out-of-memory.md",
  "content_type": "markdown",
  "chunk_count": 4,
  "ingested_at": "2026-03-26T10:00:00Z"
}
```

List all uploaded runbooks:

```bash
curl -H "X-API-Key: $API_SECRET_KEY" https://your-app.example.com/api/runbooks
```

See [docs/runbook-format.md](runbook-format.md) for recommended runbook structure and tips to get better triage results.

---

## Step 5: Fire a Test Alert

Verify the full pipeline — webhook receives → triage runs → Slack message appears.

```bash
# Fire a P1 test alert (uses localhost by default)
./scripts/test_alert.sh p1

# Fire against a remote deployment
SRE_COPILOT_URL=https://your-app.example.com ./scripts/test_alert.sh p2

# Available severities: p1, p2, p3
./scripts/test_alert.sh p3
```

Expected output:

```
Sending p1 test alert to http://localhost:8000/webhooks/pagerduty...
Incident ID: P1TEST1711444800
Response: {"status":"accepted"}
Status:   200

✓ Alert accepted. Check #incidents in Slack for the triage result.
```

Within a few seconds, a Block Kit message should appear in your `#incidents` channel with:
- Severity badge (P1/P2/P3)
- AI diagnosis
- Step-by-step immediate actions
- Interactive buttons: Resolved, Escalate, Wrong diagnosis, Ask follow-up

If the message does not appear, check:
1. `docker compose logs api` (or Railway logs) for errors
2. `curl https://your-app/ready` — both `db` and `llm` should be `"ok"`
3. Verify `SLACK_BOT_TOKEN` and `INCIDENTS_CHANNEL` are set correctly
