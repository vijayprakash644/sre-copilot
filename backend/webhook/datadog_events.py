"""
Optional: Datadog event webhook receiver.
Handles Datadog monitor alert events.
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


@router.post("/datadog")
async def datadog_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    x_datadog_signature: str = Header(default=""),
) -> dict:
    payload = await request.body()
    body = json.loads(payload)

    # Only process alert events
    event_type = body.get("event_type", "")
    if event_type not in ("metric_alert_monitor", "service_check"):
        return {"status": "ignored", "reason": f"event_type={event_type}"}

    alert_id = str(body.get("id", ""))
    dedup_key = f"dd:{alert_id}"
    if await is_duplicate_webhook(dedup_key):
        logger.info("datadog.duplicate_skipped", alert_id=alert_id)
        return {"status": "accepted"}

    await mark_webhook_processed(dedup_key)
    alert = _parse_datadog_alert(body)
    background_tasks.add_task(_process_alert, alert)

    return {"status": "accepted"}


def _parse_datadog_alert(body: dict) -> Alert:
    scrubber = get_scrubber()
    name = scrubber.scrub(body.get("title", "Datadog Alert"))
    description = scrubber.scrub(body.get("body", name))
    tags = body.get("tags", [])
    labels = {}
    for tag in tags:
        if ":" in tag:
            k, _, v = tag.partition(":")
            labels[k] = scrubber.scrub(v)

    return Alert(
        source=AlertSource.DATADOG,
        name=name,
        description=description,
        service=labels.get("service"),
        environment=labels.get("env"),
        labels=labels,
        annotations={"url": body.get("url", "")},
        fired_at=datetime.utcnow(),
        raw_payload=scrubber.scrub_dict(body),
    )


async def _process_alert(alert: Alert) -> None:
    settings = get_settings()
    try:
        await save_alert(alert)
        result = await triage_alert(alert)
        await save_triage_result(result)
        if settings.slack_bot_token:
            await post_triage_message(settings.incidents_channel, alert, result)
    except Exception as exc:
        logger.error("datadog.processing_failed", alert_id=alert.id, error=str(exc))
