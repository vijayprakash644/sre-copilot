"""
PagerDuty v3 webhook receiver.

Validates HMAC-SHA256 signature before processing any payload.
Supports: incident.triggered, incident.acknowledged, incident.resolved
Only processes incident.triggered events for triage.
"""
from __future__ import annotations

import hashlib
import hmac
import time
from datetime import datetime

import structlog
from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException, Request

from ai.scrubber import get_scrubber
from ai.triage import triage_alert
from config import get_settings
from db import is_duplicate_webhook, mark_webhook_processed, save_alert, save_triage_result
from integrations.slack import post_triage_message
from models import Alert, AlertSource

logger = structlog.get_logger()

router = APIRouter()


def _validate_pagerduty_signature(payload: bytes, signature_header: str, secret: str) -> bool:
    """Validate X-PagerDuty-Signature HMAC-SHA256 header."""
    if not secret:
        logger.warning("pagerduty.hmac_skipped_no_secret")
        return True  # Skip validation when no secret configured (dev only)

    # PagerDuty sends: "v1=<hex_digest>"
    expected_prefix = "v1="
    if not signature_header.startswith(expected_prefix):
        return False

    provided_sig = signature_header[len(expected_prefix):]
    computed = hmac.new(
        secret.encode("utf-8"),
        payload,
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(computed, provided_sig)


@router.post("/pagerduty")
async def pagerduty_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    x_pagerduty_signature: str = Header(default=""),
) -> dict:
    settings = get_settings()
    payload = await request.body()

    # Validate HMAC
    if not _validate_pagerduty_signature(
        payload, x_pagerduty_signature, settings.pagerduty_webhook_secret
    ):
        logger.warning("pagerduty.invalid_signature")
        raise HTTPException(status_code=403, detail="Invalid signature")

    body = await request.json() if not hasattr(request, "_json") else request._json

    # Re-parse since we already consumed the body
    import json
    body = json.loads(payload)

    messages = body.get("messages", [])
    if not messages:
        # Try v3 format: single event
        messages = [body]

    for message in messages:
        event_type = message.get("event", {}).get("event_type") or message.get("event_type", "")
        if event_type != "incident.triggered":
            logger.info("pagerduty.event_ignored", event_type=event_type)
            continue

        incident = (
            message.get("event", {}).get("data")
            or message.get("incident")
            or message
        )
        incident_id = str(incident.get("id", incident.get("number", "")))

        # Deduplication
        dedup_key = f"pd:{incident_id}"
        if await is_duplicate_webhook(dedup_key):
            logger.info("pagerduty.duplicate_skipped", incident_id=incident_id)
            continue

        await mark_webhook_processed(dedup_key)

        alert = _parse_pagerduty_alert(incident)
        background_tasks.add_task(_process_alert, alert)

    return {"status": "accepted"}


def _parse_pagerduty_alert(incident: dict) -> Alert:
    scrubber = get_scrubber()
    title = scrubber.scrub(incident.get("title", incident.get("summary", "PagerDuty Alert")))
    description = scrubber.scrub(
        incident.get("description", incident.get("details", title))
    )
    service_obj = incident.get("service", {})
    service = service_obj.get("name") if isinstance(service_obj, dict) else str(service_obj or "")
    service = scrubber.scrub(service or "")

    created_at_str = incident.get("created_at") or incident.get("created_on", "")
    try:
        fired_at = datetime.fromisoformat(created_at_str.replace("Z", "+00:00"))
    except Exception:
        fired_at = datetime.utcnow()

    labels = {
        "pagerduty_id": str(incident.get("id", "")),
        "urgency": str(incident.get("urgency", "")),
        "status": str(incident.get("status", "")),
    }

    return Alert(
        source=AlertSource.PAGERDUTY,
        name=title,
        description=description,
        service=service or None,
        environment=incident.get("environment", None),
        labels={k: scrubber.scrub(v) for k, v in labels.items()},
        annotations=scrubber.scrub_dict(incident.get("annotations", {})),
        fired_at=fired_at,
        raw_payload=scrubber.scrub_dict(incident),
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
        logger.error("pagerduty.processing_failed", alert_id=alert.id, error=str(exc))
