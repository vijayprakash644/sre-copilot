#!/usr/bin/env python3
"""
Seeds sample runbooks into ChromaDB.

Creates 3 sample runbooks in ./data/sample_runbooks/ and ingests them.
Run from project root: uv run python scripts/seed_runbooks.py
"""
from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

POD_OOM_KILL = """\
# Kubernetes Pod OOM Kill Runbook

## Overview
This runbook covers diagnosis and resolution of Kubernetes pods being killed
due to Out-Of-Memory (OOM) conditions.

## Symptoms
- Pod status shows `OOMKilled` in `kubectl describe`
- Container restart count increasing
- Memory usage spike before crash visible in metrics
- Application logs cut off abruptly

## Diagnosis Steps

### 1. Confirm OOM kill
```bash
kubectl describe pod <pod-name> -n <namespace>
```
Look for: `Last State: Terminated — Reason: OOMKilled`

### 2. Check current memory usage
```bash
kubectl top pods -n <namespace> --sort-by=memory
```

### 3. Check current memory limits
```bash
kubectl get pod <pod-name> -n <namespace> -o jsonpath='{.spec.containers[*].resources}'
```

### 4. Review memory trends (Grafana / Prometheus)
Query: `container_memory_working_set_bytes{namespace="<namespace>",container="<name>"}`

## Resolution

### Immediate (restore service)
```bash
# If in a deployment, trigger a rolling restart
kubectl rollout restart deployment/<deployment-name> -n <namespace>
```

### Short-term (prevent recurrence)
1. Increase memory limits in the deployment spec:
```yaml
resources:
  requests:
    memory: "512Mi"
  limits:
    memory: "1Gi"
```
Apply: `kubectl apply -f deployment.yaml`

2. Check for memory leaks in recent code changes:
```bash
git log --oneline -20
```

### Long-term
- Configure HPA to scale out before hitting memory limits
- Set up memory usage alerts at 80% of limit
- Profile the application with heap dump if OOM is recurring

## Escalation
If OOM kills persist after increasing limits, escalate to the application team
to investigate memory leaks. Attach: heap dump, flamegraph, recent git diff.
"""

DB_CONNECTION_POOL = """\
# Database Connection Pool Exhaustion Runbook

## Overview
This runbook covers diagnosis and resolution of database connection pool
exhaustion, which causes application requests to fail or queue indefinitely.

## Symptoms
- Error logs: "connection pool exhausted" / "too many connections"
- PostgreSQL error: `FATAL: remaining connection slots are reserved`
- Increased request latency and 5xx error rates
- `pg_stat_activity` showing many idle connections

## Diagnosis Steps

### 1. Check current connection count
```sql
SELECT count(*), state, wait_event_type, wait_event
FROM pg_stat_activity
GROUP BY state, wait_event_type, wait_event
ORDER BY count DESC;
```

### 2. Find long-running queries
```sql
SELECT pid, age(clock_timestamp(), query_start), usename, query
FROM pg_stat_activity
WHERE query != '<IDLE>' AND query NOT ILIKE '%pg_stat_activity%'
ORDER BY query_start ASC;
```

### 3. Check max_connections setting
```sql
SHOW max_connections;
SELECT count(*) FROM pg_stat_activity;
```

### 4. Check application pool settings
Review: `DATABASE_POOL_SIZE`, `DATABASE_MAX_OVERFLOW`, `DATABASE_POOL_TIMEOUT`

## Resolution

### Immediate
Kill long-running / idle transactions:
```sql
SELECT pg_terminate_backend(pid)
FROM pg_stat_activity
WHERE state = 'idle'
  AND query_start < NOW() - INTERVAL '5 minutes';
```

### Short-term
1. Increase `max_connections` in postgresql.conf (requires restart):
```
max_connections = 200  # increase from default 100
```
Or: `ALTER SYSTEM SET max_connections = 200;` then `pg_ctl reload`

2. Use PgBouncer connection pooler in transaction mode

### Application-side
Reduce pool size per instance if running many replicas:
```
# Per-instance pool * number_of_instances < max_connections - 10 (reserved)
DATABASE_POOL_SIZE=10
DATABASE_MAX_OVERFLOW=5
```

## Escalation
If connections remain high after killing idle ones, check for a connection leak
in the application code. Attach `pg_stat_activity` output to the incident.
"""

CERT_EXPIRY = """\
# TLS Certificate Expiry Runbook

## Overview
This runbook covers detection, verification, and renewal of expiring TLS
certificates before they cause service downtime.

## Symptoms
- Alert: certificate expiring in < 30 days
- Browser shows "Your connection is not private"
- curl error: `SSL certificate problem: certificate has expired`
- Service health checks failing with TLS errors

## Diagnosis Steps

### 1. Check certificate expiry via openssl
```bash
echo | openssl s_client -servername <domain> -connect <domain>:443 2>/dev/null \
  | openssl x509 -noout -dates
```

### 2. Check from inside the cluster
```bash
kubectl exec -it <pod-name> -- \
  openssl s_client -servername <domain> -connect <domain>:443 </dev/null 2>/dev/null \
  | openssl x509 -noout -enddate
```

### 3. List cert-manager certificates (if using cert-manager)
```bash
kubectl get certificate -A
kubectl describe certificate <name> -n <namespace>
```

## Resolution

### cert-manager (automated)
Force renewal:
```bash
kubectl annotate certificate <cert-name> -n <namespace> \
  cert-manager.io/issue-temporary-certificate="true" --overwrite
```
Monitor: `kubectl get certificaterequest -n <namespace> -w`

### Let's Encrypt (manual / certbot)
```bash
certbot renew --cert-name <domain> --dry-run  # test first
certbot renew --cert-name <domain>
```
Reload nginx/haproxy after: `nginx -s reload`

### AWS ACM
- Navigate to ACM in AWS Console
- Click "Request certificate" or check if auto-renewal is enabled
- For ALB: ensure certificate ARN is updated in listener settings

### Self-signed / internal CA
1. Generate new cert from internal CA
2. Update secret in Kubernetes:
```bash
kubectl create secret tls <name> --cert=cert.pem --key=key.pem \
  -n <namespace> --dry-run=client -o yaml | kubectl apply -f -
```
3. Restart affected deployments: `kubectl rollout restart deployment/<name>`

## Prevention
- Use cert-manager with auto-renewal (Let's Encrypt or internal CA)
- Set alerts at 30 days and 14 days before expiry
- Run weekly cron: `certbot renew --pre-hook "..." --post-hook "..."`
"""


async def main() -> None:
    from config import get_settings
    from ai.rag import get_rag_engine
    from db import init_db, save_runbook_document

    settings = get_settings()
    runbooks_dir = Path(settings.data_dir) / "sample_runbooks"
    runbooks_dir.mkdir(parents=True, exist_ok=True)

    # Write sample runbooks to disk
    samples = [
        ("pod-oom-kill.md", POD_OOM_KILL),
        ("db-connection-pool.md", DB_CONNECTION_POOL),
        ("cert-expiry.md", CERT_EXPIRY),
    ]

    print("Creating sample runbooks...")
    for filename, content in samples:
        path = runbooks_dir / filename
        path.write_text(content)
        print(f"  Created: {path}")

    # Initialize DB
    await init_db()

    # Ingest into ChromaDB
    rag = get_rag_engine()
    print("\nIngesting into ChromaDB...")

    import uuid
    for filename, _ in samples:
        path = runbooks_dir / filename
        doc_id = str(uuid.uuid5(uuid.NAMESPACE_URL, filename))
        try:
            doc = await rag.ingest_document(path, doc_id)
            await save_runbook_document(doc_id, filename, doc.content_type, doc.chunk_count)
            print(f"  ✓ {filename} — {doc.chunk_count} chunks")
        except Exception as e:
            print(f"  ✗ {filename} — failed: {e}")

    print("\nDone. Runbooks are now searchable via RAG.")


if __name__ == "__main__":
    asyncio.run(main())
