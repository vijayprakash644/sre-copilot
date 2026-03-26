"""
aiosqlite database setup and CRUD helpers.
Manages alert history and triage result persistence.
"""
from __future__ import annotations

import json
import os
from datetime import datetime
from typing import AsyncIterator

import aiosqlite
import structlog

from config import get_settings
from models import Alert, AlertSource, AlertSeverity, AlertWithTriage, TriageResult

logger = structlog.get_logger()

_CREATE_ALERTS_TABLE = """
CREATE TABLE IF NOT EXISTS alerts (
    id TEXT PRIMARY KEY,
    source TEXT NOT NULL,
    name TEXT NOT NULL,
    description TEXT NOT NULL,
    service TEXT,
    environment TEXT,
    labels TEXT NOT NULL DEFAULT '{}',
    annotations TEXT NOT NULL DEFAULT '{}',
    fired_at TEXT NOT NULL,
    raw_payload TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
)
"""

_CREATE_TRIAGE_TABLE = """
CREATE TABLE IF NOT EXISTS triage_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    alert_id TEXT NOT NULL REFERENCES alerts(id),
    severity TEXT NOT NULL,
    diagnosis TEXT NOT NULL,
    actions TEXT NOT NULL DEFAULT '[]',
    escalate_to TEXT,
    watch_out TEXT,
    runbook_sources TEXT NOT NULL DEFAULT '[]',
    past_incident_refs TEXT NOT NULL DEFAULT '[]',
    llm_model TEXT NOT NULL,
    deployment_mode TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    feedback TEXT
)
"""

_CREATE_RUNBOOKS_TABLE = """
CREATE TABLE IF NOT EXISTS runbook_documents (
    id TEXT PRIMARY KEY,
    filename TEXT NOT NULL,
    content_type TEXT NOT NULL,
    chunk_count INTEGER NOT NULL,
    ingested_at TEXT NOT NULL DEFAULT (datetime('now'))
)
"""

_CREATE_DEDUP_TABLE = """
CREATE TABLE IF NOT EXISTS processed_webhooks (
    dedup_id TEXT PRIMARY KEY,
    processed_at TEXT NOT NULL DEFAULT (datetime('now'))
)
"""


async def get_db() -> AsyncIterator[aiosqlite.Connection]:
    settings = get_settings()
    os.makedirs(os.path.dirname(os.path.abspath(settings.database_url)), exist_ok=True)
    async with aiosqlite.connect(settings.database_url) as db:
        db.row_factory = aiosqlite.Row
        yield db


async def init_db() -> None:
    settings = get_settings()
    db_path = settings.database_url
    os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)
    async with aiosqlite.connect(db_path) as db:
        await db.execute(_CREATE_ALERTS_TABLE)
        await db.execute(_CREATE_TRIAGE_TABLE)
        await db.execute(_CREATE_RUNBOOKS_TABLE)
        await db.execute(_CREATE_DEDUP_TABLE)
        await db.commit()
    logger.info("db.initialized", path=db_path)


async def check_db_health() -> bool:
    try:
        settings = get_settings()
        async with aiosqlite.connect(settings.database_url) as db:
            await db.execute("SELECT 1")
        return True
    except Exception as exc:
        logger.error("db.health_check_failed", error=str(exc))
        return False


# ── Deduplication ──────────────────────────────────────────────────────────────

async def is_duplicate_webhook(dedup_id: str, window_minutes: int = 5) -> bool:
    settings = get_settings()
    async with aiosqlite.connect(settings.database_url) as db:
        async with db.execute(
            """
            SELECT 1 FROM processed_webhooks
            WHERE dedup_id = ?
              AND processed_at > datetime('now', ?)
            """,
            (dedup_id, f"-{window_minutes} minutes"),
        ) as cursor:
            row = await cursor.fetchone()
    return row is not None


async def mark_webhook_processed(dedup_id: str) -> None:
    settings = get_settings()
    async with aiosqlite.connect(settings.database_url) as db:
        await db.execute(
            "INSERT OR REPLACE INTO processed_webhooks (dedup_id) VALUES (?)",
            (dedup_id,),
        )
        await db.commit()


# ── Alerts ─────────────────────────────────────────────────────────────────────

async def save_alert(alert: Alert) -> None:
    settings = get_settings()
    async with aiosqlite.connect(settings.database_url) as db:
        await db.execute(
            """
            INSERT OR REPLACE INTO alerts
            (id, source, name, description, service, environment,
             labels, annotations, fired_at, raw_payload)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                alert.id,
                alert.source.value,
                alert.name,
                alert.description,
                alert.service,
                alert.environment,
                json.dumps(alert.labels),
                json.dumps(alert.annotations),
                alert.fired_at.isoformat(),
                json.dumps(alert.raw_payload),
            ),
        )
        await db.commit()


async def save_triage_result(result: TriageResult) -> None:
    settings = get_settings()
    async with aiosqlite.connect(settings.database_url) as db:
        await db.execute(
            """
            INSERT INTO triage_results
            (alert_id, severity, diagnosis, actions, escalate_to, watch_out,
             runbook_sources, past_incident_refs, llm_model, deployment_mode,
             created_at, feedback)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                result.alert_id,
                result.severity.value,
                result.diagnosis,
                json.dumps(result.actions),
                result.escalate_to,
                result.watch_out,
                json.dumps(result.runbook_sources),
                json.dumps(result.past_incident_refs),
                result.llm_model,
                result.deployment_mode,
                result.created_at.isoformat(),
                result.feedback,
            ),
        )
        await db.commit()


async def get_alerts(limit: int = 50, offset: int = 0) -> list[AlertWithTriage]:
    settings = get_settings()
    results = []
    async with aiosqlite.connect(settings.database_url) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM alerts ORDER BY fired_at DESC LIMIT ? OFFSET ?",
            (limit, offset),
        ) as cursor:
            rows = await cursor.fetchall()

        for row in rows:
            alert = _row_to_alert(row)
            triage = await _get_triage_for_alert(db, alert.id)
            results.append(AlertWithTriage(alert=alert, triage=triage))

    return results


async def get_alert_by_id(alert_id: str) -> AlertWithTriage | None:
    settings = get_settings()
    async with aiosqlite.connect(settings.database_url) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM alerts WHERE id = ?", (alert_id,)
        ) as cursor:
            row = await cursor.fetchone()
        if not row:
            return None
        alert = _row_to_alert(row)
        triage = await _get_triage_for_alert(db, alert_id)
    return AlertWithTriage(alert=alert, triage=triage)


async def update_triage_feedback(alert_id: str, rating: str) -> None:
    settings = get_settings()
    async with aiosqlite.connect(settings.database_url) as db:
        await db.execute(
            "UPDATE triage_results SET feedback = ? WHERE alert_id = ?",
            (rating, alert_id),
        )
        await db.commit()


async def get_alert_stats() -> dict:
    settings = get_settings()
    async with aiosqlite.connect(settings.database_url) as db:
        async with db.execute("SELECT COUNT(*) FROM alerts") as cur:
            total = (await cur.fetchone())[0]
        async with db.execute(
            "SELECT COUNT(*) FROM triage_results WHERE severity = 'P1'"
        ) as cur:
            p1 = (await cur.fetchone())[0]
        async with db.execute(
            "SELECT COUNT(*) FROM triage_results WHERE severity = 'P2'"
        ) as cur:
            p2 = (await cur.fetchone())[0]
        async with db.execute(
            "SELECT COUNT(*) FROM triage_results WHERE severity = 'P3'"
        ) as cur:
            p3 = (await cur.fetchone())[0]
        async with db.execute(
            "SELECT COUNT(*) FROM triage_results WHERE feedback IS NOT NULL"
        ) as cur:
            feedback_total = (await cur.fetchone())[0]
        async with db.execute(
            "SELECT COUNT(*) FROM triage_results WHERE feedback = 'good'"
        ) as cur:
            feedback_good = (await cur.fetchone())[0]

    good_rate = (feedback_good / feedback_total) if feedback_total > 0 else 0.0
    return {
        "total_alerts": total,
        "p1_count": p1,
        "p2_count": p2,
        "p3_count": p3,
        "feedback_good_rate": round(good_rate, 2),
    }


# ── Runbooks ───────────────────────────────────────────────────────────────────

async def save_runbook_document(doc_id: str, filename: str, content_type: str, chunk_count: int) -> None:
    settings = get_settings()
    async with aiosqlite.connect(settings.database_url) as db:
        await db.execute(
            """
            INSERT OR REPLACE INTO runbook_documents
            (id, filename, content_type, chunk_count)
            VALUES (?, ?, ?, ?)
            """,
            (doc_id, filename, content_type, chunk_count),
        )
        await db.commit()


async def get_runbook_documents() -> list[dict]:
    settings = get_settings()
    async with aiosqlite.connect(settings.database_url) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM runbook_documents ORDER BY ingested_at DESC"
        ) as cursor:
            rows = await cursor.fetchall()
    return [dict(r) for r in rows]


async def delete_runbook_document(doc_id: str) -> bool:
    settings = get_settings()
    async with aiosqlite.connect(settings.database_url) as db:
        async with db.execute(
            "DELETE FROM runbook_documents WHERE id = ?", (doc_id,)
        ) as cursor:
            deleted = cursor.rowcount > 0
        await db.commit()
    return deleted


# ── Helpers ────────────────────────────────────────────────────────────────────

def _row_to_alert(row: aiosqlite.Row) -> Alert:
    return Alert(
        id=row["id"],
        source=AlertSource(row["source"]),
        name=row["name"],
        description=row["description"],
        service=row["service"],
        environment=row["environment"],
        labels=json.loads(row["labels"]),
        annotations=json.loads(row["annotations"]),
        fired_at=datetime.fromisoformat(row["fired_at"]),
        raw_payload=json.loads(row["raw_payload"]),
    )


async def _get_triage_for_alert(db: aiosqlite.Connection, alert_id: str) -> TriageResult | None:
    async with db.execute(
        "SELECT * FROM triage_results WHERE alert_id = ? ORDER BY created_at DESC LIMIT 1",
        (alert_id,),
    ) as cursor:
        row = await cursor.fetchone()
    if not row:
        return None
    return TriageResult(
        alert_id=row["alert_id"],
        severity=AlertSeverity(row["severity"]),
        diagnosis=row["diagnosis"],
        actions=json.loads(row["actions"]),
        escalate_to=row["escalate_to"],
        watch_out=row["watch_out"],
        runbook_sources=json.loads(row["runbook_sources"]),
        past_incident_refs=json.loads(row["past_incident_refs"]),
        llm_model=row["llm_model"],
        deployment_mode=row["deployment_mode"],
        created_at=datetime.fromisoformat(row["created_at"]),
        feedback=row["feedback"],
    )
