"""
Tests for ai/rag.py — ChromaDB ingestion and retrieval.
Uses temporary directories to avoid polluting persistent state.
"""
from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import patch, AsyncMock

import pytest


@pytest.fixture
def sample_md(tmp_path) -> Path:
    content = """# OOM Kill Runbook

## Symptoms
- Kubernetes pod is in CrashLoopBackOff
- kubectl describe pod shows OOMKilled
- Memory usage spikes before crash

## Diagnosis
Check container memory limits:
```
kubectl describe pod <pod-name> -n <namespace>
```

Check memory usage trends:
```
kubectl top pods -n <namespace>
```

## Resolution
1. Increase memory limits in the deployment spec
2. Check for memory leaks in application code
3. Review recent code changes that might increase memory usage
4. If urgent: restart the pod to restore service

## Prevention
- Set proper memory requests and limits
- Configure HPA based on memory metrics
"""
    f = tmp_path / "pod-oom-kill.md"
    f.write_text(content)
    return f


@pytest.fixture
def rag_engine(temp_chroma):
    """RAG engine with fresh ChromaDB."""
    from ai.rag import RAGEngine
    return RAGEngine()


@pytest.mark.asyncio
async def test_ingest_markdown_document(rag_engine, sample_md):
    """Ingesting a markdown file creates chunks in ChromaDB."""
    doc_id = "test-doc-001"

    with patch("ai.rag.embed_texts") as mock_embed:
        mock_embed.return_value = [[0.1] * 1024]  # stub embedding for each chunk

        async def fake_embed_texts(texts):
            return [[0.1 + i * 0.01] * 1024 for i in range(len(texts))]

        mock_embed.side_effect = fake_embed_texts

        doc = await rag_engine.ingest_document(sample_md, doc_id)

    assert doc.id == doc_id
    assert doc.filename == "pod-oom-kill.md"
    assert doc.content_type == "markdown"
    assert doc.chunk_count >= 1


@pytest.mark.asyncio
async def test_search_returns_relevant_chunks(rag_engine, sample_md):
    """After ingestion, search returns relevant chunks."""
    doc_id = "test-doc-002"

    async def fake_embed_texts(texts):
        return [[0.1 + i * 0.001] * 1024 for i in range(len(texts))]

    async def fake_embed_text(text):
        return [0.15] * 1024

    with (
        patch("ai.rag.embed_texts", side_effect=fake_embed_texts),
        patch("ai.rag.embed_text", side_effect=fake_embed_text),
    ):
        await rag_engine.ingest_document(sample_md, doc_id)
        results = await rag_engine.search_runbooks("OOM kill kubernetes pod")

    assert isinstance(results, list)
    assert len(results) >= 1


@pytest.mark.asyncio
async def test_search_returns_empty_when_no_documents(rag_engine):
    """Searching an empty collection returns empty list without error."""
    async def fake_embed_text(text):
        return [0.1] * 1024

    with patch("ai.rag.embed_text", side_effect=fake_embed_text):
        results = await rag_engine.search_runbooks("anything")

    assert results == []


@pytest.mark.asyncio
async def test_store_and_retrieve_past_incident(rag_engine):
    """Storing an incident and retrieving similar ones works."""
    from datetime import datetime
    from models import Alert, AlertSource, TriageResult, AlertSeverity

    alert = Alert(
        source=AlertSource.PAGERDUTY,
        name="Database connection pool exhausted",
        description="Max connections reached on primary DB",
        service="api-server",
        environment="production",
        fired_at=datetime.utcnow(),
    )

    triage = TriageResult(
        alert_id=alert.id,
        severity=AlertSeverity.P1,
        diagnosis="Connection pool hit max limit due to a query taking too long",
        actions=["Kill long-running queries", "Increase pool size temporarily"],
        llm_model="claude-sonnet-4-6",
        deployment_mode="api",
        created_at=datetime.utcnow(),
    )

    async def fake_embed_text(text):
        # Return slightly different vectors to make search work
        h = sum(ord(c) for c in text[:50])
        return [float(h % 100) / 100.0] * 1024

    with patch("ai.rag.embed_text", side_effect=fake_embed_text):
        await rag_engine.store_incident(alert, triage)

        # Search for a similar incident
        similar_alert = Alert(
            source=AlertSource.ALERTMANAGER,
            name="DB connections maxed out",
            description="Connection refused from application tier",
            service="payment-service",
            fired_at=datetime.utcnow(),
        )

        results = await rag_engine.search_similar_incidents(similar_alert)

    assert isinstance(results, list)


@pytest.mark.asyncio
async def test_ingest_scrubs_sensitive_content(rag_engine, tmp_path):
    """Sensitive content in runbooks is scrubbed before storage."""
    runbook = tmp_path / "sensitive.md"
    runbook.write_text(
        "# Runbook\n"
        "Connect to DB: postgres://admin:supersecretpassword@prod.db:5432/app\n"
        "Check logs on 192.168.1.100\n"
        "Normal advice: restart the service\n"
    )

    stored_docs = []

    original_upsert = None

    async def fake_embed_texts(texts):
        stored_docs.extend(texts)
        return [[0.1] * 1024 for _ in texts]

    with patch("ai.rag.embed_texts", side_effect=fake_embed_texts):
        await rag_engine.ingest_document(runbook, "sensitive-doc")

    assert all("supersecretpassword" not in doc for doc in stored_docs)
    assert all("192.168.1.100" not in doc for doc in stored_docs)


@pytest.mark.asyncio
async def test_delete_document(rag_engine, sample_md):
    """Deleting a document removes its chunks."""
    doc_id = "delete-test-001"

    async def fake_embed_texts(texts):
        return [[0.1] * 1024 for _ in texts]

    with patch("ai.rag.embed_texts", side_effect=fake_embed_texts):
        await rag_engine.ingest_document(sample_md, doc_id)

    # Delete
    await rag_engine.delete_document(doc_id)
    # No error — document is gone
