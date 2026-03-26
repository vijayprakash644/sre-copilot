# SRE Copilot — Runbook Format Guide

SRE Copilot uses Retrieval-Augmented Generation (RAG) to inject relevant runbook content into the triage prompt. The quality of the AI's diagnosis and action steps is directly proportional to how well-structured and specific your runbooks are. This guide explains how to write runbooks that maximise triage quality.

---

## How RAG Uses Your Runbooks

When an alert fires, SRE Copilot:

1. Builds a query string from the alert name, description, and service.
2. Embeds the query using Anthropic's `voyage-3` embedding model.
3. Retrieves the top 3 most semantically similar chunks from your uploaded runbooks.
4. Injects those chunks into the triage prompt as context.

Runbooks are split into ~512-token chunks with 50-token overlap. Each chunk is embedded and stored independently. **This means every chunk must be independently useful** — do not rely on the LLM receiving a whole document in sequence.

---

## Supported File Formats

| Format | Extension | Notes |
|---|---|---|
| Markdown | `.md` | Preferred. Headers, code blocks, and bullet lists are preserved. |
| PDF | `.pdf` | Text is extracted via `pypdf`. Complex layouts (tables, multi-column) may not extract cleanly. Prefer Markdown when possible. |

Upload via:

```bash
curl -X POST https://your-app/api/runbooks/upload \
  -H "X-API-Key: $API_SECRET_KEY" \
  -F "file=@./runbooks/redis-out-of-memory.md"
```

---

## Recommended Runbook Structure

Each runbook should cover a single alert type or a closely related group of alerts. The following structure produces the best RAG retrieval results:

```markdown
# <Alert Name> — Runbook

## Overview
One paragraph: what this alert means, what system is affected, and what the impact is.
Include the exact alert name as it appears in PagerDuty/AlertManager — this dramatically
improves semantic matching.

## Symptoms
- What you will see in Slack/PagerDuty (alert name, threshold)
- What users will experience
- What metrics will be elevated/degraded

## Diagnosis
### Step 1: Confirm the alert is real
Command or procedure to verify the issue is genuine (not a flapping sensor).

### Step 2: Identify the root cause
Commands to run, metrics to check, log queries to execute.
Include the exact commands — the LLM will surface these verbatim.

### Step 3: Check related systems
Dependencies that may be the actual cause.

## Resolution
### Quick fix (< 5 minutes)
Step-by-step commands to resolve the most common cause.

### If the quick fix doesn't work
Alternative resolution paths.

## Prevention
What change reduces the probability of recurrence.

## Escalation
Who to contact and when (after X minutes unresolved, or if Y condition applies).
```

---

## File Naming

Use descriptive, lowercase, hyphenated filenames that match alert names. Good naming improves retrieval because the filename is included as metadata:

| Good | Bad |
|---|---|
| `redis-out-of-memory.md` | `runbook1.md` |
| `kubernetes-pod-crashloopbackoff.md` | `k8s.md` |
| `high-cpu-api-server.md` | `CPU issue.pdf` |
| `postgres-replication-lag.md` | `Database Runbook v3 FINAL.pdf` |

---

## Good vs Bad Examples

### Example: High CPU Alert Runbook

**Bad — too generic, no actionable commands:**

```markdown
# High CPU

If CPU is high, check what processes are using it. Kill the ones that are using too much.
Restart the service if needed. Contact the team if it doesn't improve.
```

Problems with this runbook:
- No specific commands
- No thresholds or context
- No escalation path
- Will not match well for "api-server CPU 95%" vs "worker-node CPU 80%" — they would share the same generic chunk

**Good — specific, command-first, includes alert context:**

```markdown
# HIGH CPU: api-server — Runbook

## Overview
Fires when `api-server` CPU usage exceeds 90% sustained for 10 minutes.
This alert indicates the service is CPU-saturated and request latency is likely elevated.
Impact: increased P99 latency, potential request timeouts.

## Diagnosis

### 1. Confirm the alert
```bash
kubectl top pods -n production -l app=api-server
```
If all pods are showing >85% CPU, the issue is real.

### 2. Check for traffic spike
```bash
kubectl logs -n production -l app=api-server --since=15m | grep "POST /api" | wc -l
```
Compare to baseline (~2000 req/min). If 5x higher, it's a traffic spike.

### 3. Check for a runaway goroutine / thread
```bash
curl -s http://api-server-pod-ip:6060/debug/pprof/goroutine?debug=1 | head -50
```

## Resolution

### Traffic spike
Scale up the deployment:
```bash
kubectl scale deployment api-server -n production --replicas=6
```
Wait 2 minutes and verify CPU drops below 70%.

### Runaway process
Rolling restart:
```bash
kubectl rollout restart deployment/api-server -n production
kubectl rollout status deployment/api-server -n production
```

## Escalation
If CPU remains above 90% after scaling and rolling restart, escalate to the Platform team.
Check if a recent deployment correlates: `kubectl rollout history deployment/api-server -n production`
```

This runbook will produce highly specific triage output because:
- The alert name appears verbatim
- Commands are copy-pasteable with no placeholders
- Resolution steps are ordered by likelihood
- Escalation path is explicit

---

## Tips for Maximum Triage Quality

**1. Include exact alert names.**
The scrubbed alert name is used as the RAG query. If your runbook says "High CPU on api-server" and the alert fires as "HIGH CPU: api-server CPU usage at 95%", they will match well. If your runbook says "Performance issues", it will not match.

**2. Put the most important content first.**
Each 512-token chunk is scored independently. If your runbook has a long "Background" section before the commands, the background section may be retrieved instead of the commands. Lead with actionable content.

**3. One runbook per alert type.**
A single runbook covering 20 different alert types will produce mediocre results for all of them. Write a focused runbook for each distinct alert.

**4. Use real commands, not placeholders.**
The system prompt instructs Claude: "If you reference a command, it must be runnable copy-paste (no placeholders like `<your-value>`)." Your runbooks should follow the same principle. Use actual namespace names, service names, and metric names from your environment.

**5. Include failure modes and gotchas.**
The triage prompt has a `<watch_out>` field specifically for "Common pitfall or gotcha specific to this type of incident." If your runbook includes a section like "Warning: rolling restart will cause a 30-second window of 503s — announce in #incidents first", Claude will surface this in the `watch_out` field.

**6. Keep PDFs simple.**
If using PDF, prefer single-column documents with no embedded images. `pypdf` extracts text layer content; tables and diagrams are not extracted. Convert complex PDFs to Markdown before uploading.

**7. Update runbooks after incidents.**
After resolving an incident, update the runbook with what actually worked. SRE Copilot also stores past incident summaries in ChromaDB automatically, but the runbook is the ground truth your team has validated.

---

## Chunk Size Reference

| Setting | Default | Effect |
|---|---|---|
| Chunk size | ~512 tokens (~2048 chars) | Larger = more context per chunk, fewer chunks retrieved |
| Chunk overlap | ~50 tokens (~200 chars) | Prevents context loss at boundaries |
| `MAX_RUNBOOK_CHUNKS` | 3 | Number of chunks injected per triage call |

These values are configured in `backend/ai/rag.py`. The defaults are tuned for Claude Sonnet's context window and typical runbook content density.
