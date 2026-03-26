"""
Datadog Logs API client.
Fetches recent log lines for a service to provide log context for triage.
"""
from __future__ import annotations

from datetime import datetime, timedelta

import httpx
import structlog

from ai.scrubber import get_scrubber
from config import get_settings

logger = structlog.get_logger()


async def fetch_logs(
    service: str,
    window_minutes: int = 30,
    max_lines: int = 20,
) -> list[str]:
    """
    Fetch recent logs for a service from Datadog Logs API.
    Returns scrubbed log lines.
    Returns empty list if DATADOG_API_KEY not configured — fails gracefully.
    """
    settings = get_settings()

    if not settings.datadog_api_key or not settings.datadog_app_key:
        logger.debug("datadog.not_configured")
        return []

    scrubber = get_scrubber()
    now = datetime.utcnow()
    start = now - timedelta(minutes=window_minutes)

    url = f"https://api.{settings.datadog_site}/api/v2/logs/events/search"
    headers = {
        "DD-API-KEY": settings.datadog_api_key,
        "DD-APPLICATION-KEY": settings.datadog_app_key,
        "Content-Type": "application/json",
    }
    body = {
        "filter": {
            "query": f"service:{service}",
            "from": start.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "to": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        },
        "sort": "-timestamp",
        "page": {"limit": max_lines},
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(url, json=body, headers=headers)
            response.raise_for_status()

        data = response.json()
        events = data.get("data", [])
        lines = []
        for event in events:
            attrs = event.get("attributes", {})
            message = attrs.get("message", attrs.get("text", ""))
            if message:
                lines.append(scrubber.scrub(str(message)))

        logger.info("datadog.logs_fetched", service=service, count=len(lines))
        return lines

    except Exception as exc:
        logger.warning("datadog.fetch_failed", service=service, error=str(exc))
        return []
