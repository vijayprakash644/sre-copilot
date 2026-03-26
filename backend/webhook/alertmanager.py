"""
Prometheus AlertManager webhook receiver.

Accepts AlertManager v2 webhook format.
Validates with shared secret in Authorization: Bearer <secret> header.
Processes 'firing' alerts only.
"""
from __future__ import annotations

import json
from datetime import datetime

import structlog
from fastapi import APIRouter, BackgroundTasks, Header, HTTPException, Request

from ai.scrubber import get_scrubber
from ai.triage import triage_alert
from config import get_settings
from db import is_duplicate_webhook, mark_webhook_processed, save_alert, save_triage_result
from integrations.slack import post_triage_message
from models import Alert, AlertSource

logger = structlog.get_logger()

router = APIRouter()


@router.post("/alertmanager")
async def alertmanager_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    authorization: str = Header(default=""),
) -> dict:
    settings = get_settings()

    # Validate Bearer token
    expected_token = settings.pagerduty_webhook_secret  # reuse same secret field or use dedicated
    if expected_token:
        if not authorization.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Missing Bearer token")
        token = authorization[len("Bearer "):]
        if token != expected_token:
            logger.warning("alertmanager.invalid_token")
            raise HTTPException(status_code=403, detail="Invalid token")

    payload = await request.body()
    body = json.loads(payload)

    alerts_payload = body.get("alerts", [])
    for raw_alert in alerts_payload:
        if raw_alert.get("status", "") != "firing":
            continue

        # Deduplication using fingerprint or labels hash
        fingerprint = raw_alert.get("fingerprint") or _fingerprint(raw_alert)
        dedup_key = f"am:{fingerprint}"

        if await is_duplicate_webhook(dedup_key):
            logger.info("alertmanager.duplicate_skipped", fingerprint=fingerprint)
            continue

        await mark_webhook_processed(dedup_key)
        alert = _parse_alertmanager_alert(raw_alert)
        background_tasks.add_task(_process_alert, alert)

    return {"status": "accepted"}


def _parse_alertmanager_alert(raw: dict) -> Alert:
    scrubber = get_scrubber()
    labels = {str(k): scrubber.scrub(str(v)) for k, v in raw.get("labels", {}).items()}
    annotations = {str(k): scrubber.scrub(str(v)) for k, v in raw.get("annotations", {}).items()}

    name = labels.get("alertname", annotations.get("summary", "AlertManager Alert"))
    description = annotations.get("description", annotations.get("message", name))
    service = labels.get("service", labels.get("job", None))
    environment = labels.get("env", labels.get("environment", None))

    starts_at_str = raw.get("startsAt", "")
    try:
        fired_at = datetime.fromisoformat(starts_at_str.replace("Z", "+00:00"))
    except Exception:
        fired_at = datetime.utcnow()

    return Alert(
        source=AlertSource.ALERTMANAGER,
        name=scrubber.scrub(name),
        description=scrubber.scrub(description),
        service=service,
        environment=environment,
        labels=labels,
        annotations=annotations,
        fired_at=fired_at,
        raw_payload=scrubber.scrub_dict(raw),
    )


def _fingerprint(raw: dict) -> str:
    """Compute a stable fingerprint from alert labels when fingerprint field absent."""
    import hashlib

    labels = raw.get("labels", {})
    key = "&".join(f"{k}={v}" for k, v in sorted(labels.items()))
    return hashlib.sha256(key.encode()).hexdigest()[:16]


async def _process_alert(alert: Alert) -> None:
    settings = get_settings()
    try:
        await save_alert(alert)
        result = await triage_alert(alert)
        await save_triage_result(result)

        if settings.slack_bot_token:
            await post_triage_message(settings.incidents_channel, alert, result)

    except Exception as exc:
        logger.error("alertmanager.processing_failed", alert_id=alert.id, error=str(exc))
