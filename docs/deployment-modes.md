# SRE Copilot — Deployment Modes

SRE Copilot selects its LLM backend via the `DEPLOYMENT_MODE` environment variable. The four modes differ in where inference runs, who sees your data, and what credentials are required. All other SRE Copilot behaviour (webhook ingestion, scrubbing, RAG, Slack posting) is identical across all modes.

---

## Mode Comparison

| | `api` | `bedrock` (us-east-1) | `ollama` | `bedrock` (ap-northeast-1) |
|---|---|---|---|---|
| Inference runs in | Anthropic cloud | Your AWS account | Your own server | Your AWS account (Tokyo) |
| Data leaves your network | Yes (to Anthropic) | No | No | No |
| Credentials required | `ANTHROPIC_API_KEY` | AWS IAM | None (local) | AWS IAM |
| GPU required | No | No (managed) | Yes (recommended) | No (managed) |
| APPI data-in-Japan | No | No | If hosted in Japan | Yes |
| Easiest setup | Yes | Medium | Harder | Medium |

---

## Mode 1: `api` — Anthropic API

The default mode. Inference is handled by Anthropic's hosted Claude API.

**When to use:** You want the fastest setup and are comfortable with data leaving your network to Anthropic (see [privacy-security.md](privacy-security.md) for Anthropic's retention policy).

### Setup

```env
DEPLOYMENT_MODE=api
ANTHROPIC_API_KEY=sk-ant-api03-...
ANTHROPIC_MODEL=claude-sonnet-4-6-20250514-1
```

Get an API key at [https://console.anthropic.com](https://console.anthropic.com).

### Notes

- The model default (`claude-sonnet-4-6-20250514-1`) is the same model used during development and testing.
- Embeddings also use the Anthropic API (`voyage-3` model) for semantic runbook search. Both inference and embeddings are covered by the same API key.
- With Zero Data Retention (ZDR) enabled on your Anthropic account, prompts are not stored. Contact Anthropic's sales team to enable ZDR.
- The application retries failed LLM calls up to 3 times with exponential backoff (1s, 2s, 4s) via `tenacity`.
- Hard timeout per triage call: `TRIAGE_TIMEOUT_SECONDS` (default: 15 seconds).

---

## Mode 2: `bedrock` — AWS Bedrock (default region: `us-east-1`)

Inference runs inside your AWS account through the AWS Bedrock managed service. No data is sent to Anthropic's servers.

**When to use:** You have existing AWS infrastructure, strict data residency requirements outside Japan, or enterprise security policies that prohibit sending operational data to third-party APIs.

### Prerequisites

1. Enable model access for `anthropic.claude-sonnet-4-6-20250514-v1:0` in the AWS console:
   - Go to **Amazon Bedrock → Model access → Manage model access**
   - Enable **Claude Sonnet** from Anthropic
   - Wait for access to be granted (usually instant, occasionally takes a few minutes)

2. Create an IAM role or user with the minimal Bedrock permissions:

   ```json
   {
     "Version": "2012-10-17",
     "Statement": [
       {
         "Effect": "Allow",
         "Action": "bedrock:InvokeModel",
         "Resource": "arn:aws:bedrock:us-east-1::foundation-model/anthropic.claude-sonnet-4-6-20250514-v1:0"
       }
     ]
   }
   ```

   See [infra/terraform/bedrock-mode/iam.tf](../infra/terraform/bedrock-mode/iam.tf) for the complete Terraform definition.

### Setup

**Option A — IAM user credentials (simpler, less secure):**

```env
DEPLOYMENT_MODE=bedrock
AWS_REGION=us-east-1
BEDROCK_MODEL=anthropic.claude-sonnet-4-6-20250514-v1:0
AWS_ACCESS_KEY_ID=AKIA...
AWS_SECRET_ACCESS_KEY=...
```

**Option B — IAM instance/task role (recommended for ECS/EC2):**

```env
DEPLOYMENT_MODE=bedrock
AWS_REGION=us-east-1
BEDROCK_MODEL=anthropic.claude-sonnet-4-6-20250514-v1:0
# Do not set AWS_ACCESS_KEY_ID or AWS_SECRET_ACCESS_KEY
# The SDK picks up credentials from the instance metadata service
```

Attach the IAM role to your ECS task definition or EC2 instance profile. See [infra/terraform/bedrock-mode/](../infra/terraform/bedrock-mode/) for a complete ECS + IAM Terraform module.

### Notes

- Embeddings (`voyage-3`) still call the Anthropic API for semantic runbook search. If you need embeddings to stay inside AWS too, set `ANTHROPIC_API_KEY=""` — the system falls back to a deterministic stub embedding (functional but lower RAG quality).
- AWS CloudTrail logs all `bedrock:InvokeModel` calls, giving you a full audit trail.
- Bedrock does not charge for tokens in failed calls that return errors.

---

## Mode 3: `ollama` — Self-Hosted (air-gapped)

Inference runs on a local Ollama server. No data leaves your network at all (assuming embeddings fallback is also active — see below).

**When to use:** Air-gapped environments, regulated industries, on-premise deployments, or cost optimisation at high alert volume.

### Prerequisites

Install Ollama on a machine with sufficient resources:

```bash
# Install Ollama (Linux)
curl -fsSL https://ollama.com/install.sh | sh

# Pull a model (llama3.1:8b is the default; requires ~5GB VRAM)
ollama pull llama3.1:8b

# For higher quality triage (requires ~48GB VRAM):
ollama pull llama3.1:70b
```

A GPU is strongly recommended. On CPU-only inference, triage calls will likely exceed the 15-second default timeout.

### Setup

```env
DEPLOYMENT_MODE=ollama
OLLAMA_BASE_URL=http://your-ollama-server:11434
OLLAMA_MODEL=llama3.1:8b
# ANTHROPIC_API_KEY is not needed for inference
# If you leave it unset, embeddings fall back to stub mode (reduced RAG quality)
```

If SRE Copilot is running in Docker and Ollama is on the host:

```env
OLLAMA_BASE_URL=http://host.docker.internal:11434
```

### Fully Air-Gapped Setup

To ensure zero external API calls (including embeddings):

```env
DEPLOYMENT_MODE=ollama
OLLAMA_BASE_URL=http://your-ollama-server:11434
OLLAMA_MODEL=llama3.1:8b
ANTHROPIC_API_KEY=   # Leave empty to activate stub embeddings
```

With stub embeddings active, runbook RAG still works (it uses deterministic hash-based vectors) but semantic similarity will be lower. For production air-gapped deployments, consider integrating a local embedding model via the `add_pattern` / custom embedding path.

### Notes

- SRE Copilot communicates with Ollama via its OpenAI-compatible HTTP API (`POST /api/generate`).
- The `TRIAGE_TIMEOUT_SECONDS` setting (default: 15) may need to be increased for larger models on limited hardware.
- Retry logic (3 attempts, exponential backoff) applies equally to Ollama calls.

---

## Mode 4: `bedrock` in `ap-northeast-1` — APPI Compliance (Japan)

Identical to Mode 2 but with the region set to AWS Tokyo (`ap-northeast-1`). All data at rest and in transit stays within Japan, satisfying APPI data residency requirements.

**When to use:** Japanese customers or any organisation processing data subject to APPI, or customers that need data to remain within Japan's borders.

### Setup

```env
DEPLOYMENT_MODE=bedrock
AWS_REGION=ap-northeast-1
BEDROCK_MODEL=anthropic.claude-sonnet-4-6-20250514-v1:0
# Credentials via IAM role (preferred) or:
AWS_ACCESS_KEY_ID=AKIA...
AWS_SECRET_ACCESS_KEY=...
```

### Prerequisites

1. Enable model access in `ap-northeast-1` specifically:
   - In the AWS console, switch to the **Asia Pacific (Tokyo)** region
   - Go to **Amazon Bedrock → Model access** and request access to Claude Sonnet

2. Deploy SRE Copilot itself within `ap-northeast-1` (e.g., ECS Fargate in Tokyo). If the application runs outside Japan, data in transit may cross Japanese borders even if Bedrock is in Tokyo. See [infra/terraform/bedrock-mode/](../infra/terraform/bedrock-mode/) and set `variable "aws_region"` to `ap-northeast-1`.

3. Ensure your SQLite and ChromaDB data volumes are also stored within Japan (EBS volumes in `ap-northeast-1` for EC2/ECS).

### APPI Notes

See [privacy-security.md](privacy-security.md#appi-compliance-notes-for-japanese-customers) for full APPI compliance guidance, including custom scrubbing patterns for additional personal data types.

---

## Switching Modes

Changing `DEPLOYMENT_MODE` requires a restart. The LLM client is a singleton that is initialised once on startup. The scrubber, RAG engine, and all other components are mode-agnostic — only the LLM client changes.

After switching modes, run the readiness check to confirm the new LLM connection is healthy:

```bash
curl https://your-app/ready
# Expected: {"status":"ok","db":"ok","llm":"ok"}
```
