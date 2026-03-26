# SRE Copilot — Railway Deployment

Railway is the fastest way to get SRE Copilot running with a public HTTPS URL. It reads `infra/railway.toml` from the repository root and builds the container using `infra/Dockerfile`.

No Terraform is required for Railway deployments. This directory exists as a placeholder and for notes.

---

## How Railway Builds and Runs SRE Copilot

From `infra/railway.toml`:

```toml
[build]
builder = "DOCKERFILE"
dockerfilePath = "infra/Dockerfile"

[deploy]
startCommand = "uvicorn main:app --host 0.0.0.0 --port $PORT"
healthcheckPath = "/health"
healthcheckTimeout = 30
restartPolicyType = "ON_FAILURE"
restartPolicyMaxRetries = 3
```

- Railway injects `$PORT` automatically. The start command respects it.
- The `/health` endpoint is polled every 30 seconds as a liveness check.
- The service restarts automatically on failure, up to 3 times.

---

## Deploy Steps

1. Push the repository to GitHub (or fork it).
2. In [Railway](https://railway.app), click **New Project → Deploy from GitHub repo**.
3. Select your repository. Railway detects `railway.toml` and starts the first build.
4. Once deployed, go to **Settings → Networking → Generate Domain** to get a public HTTPS URL.
5. Set all required environment variables under **Variables**:

```
DEPLOYMENT_MODE=api
ANTHROPIC_API_KEY=sk-ant-...
SLACK_BOT_TOKEN=xoxb-...
SLACK_SIGNING_SECRET=...
INCIDENTS_CHANNEL=#incidents
PAGERDUTY_WEBHOOK_SECRET=<your-secret>
API_SECRET_KEY=<openssl rand -hex 32>
APP_ENV=production
```

---

## Persistent Storage

By default, Railway containers are ephemeral — SQLite and ChromaDB data is lost on redeploy. To persist data:

1. In Railway, add a **Volume** to your service.
2. Set the mount path to `/data`.
3. Set these environment variables so SRE Copilot writes to the volume:

```
DATABASE_URL=/data/sre_copilot.db
CHROMA_PERSIST_DIR=/data/chroma
DATA_DIR=/data
```

Without a volume, runbooks must be re-uploaded after every redeploy.

---

## Deployment Mode on Railway

Railway works with any of the four deployment modes:

| Mode | Notes |
|---|---|
| `api` | Default. Set `ANTHROPIC_API_KEY`. |
| `bedrock` | Set `AWS_REGION`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`. |
| `ollama` | Ollama server must be reachable from Railway. Set `OLLAMA_BASE_URL`. |
| `bedrock` (ap-northeast-1) | Set `AWS_REGION=ap-northeast-1`. Note: data transits through Railway's infrastructure before reaching Bedrock — this may not satisfy strict APPI data-in-Japan requirements. For APPI compliance, deploy SRE Copilot itself in Japan (e.g., AWS ECS in ap-northeast-1). |

---

## Useful Railway CLI Commands

```bash
# Install Railway CLI
npm install -g @railway/cli

# Login
railway login

# Link to your project
railway link

# View logs
railway logs

# Set an environment variable
railway variables set ANTHROPIC_API_KEY=sk-ant-...

# Trigger a redeploy
railway redeploy
```
