"""
AWS CloudWatch Logs client.
Fetches recent log events for log context enrichment during triage.
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta

import structlog

from ai.scrubber import get_scrubber
from config import get_settings

logger = structlog.get_logger()


async def fetch_logs(
    log_group: str | None = None,
    log_stream: str | None = None,
    window_minutes: int = 30,
    max_lines: int = 20,
) -> list[str]:
    """
    Fetch recent CloudWatch log events.
    Returns scrubbed log lines. Fails gracefully if AWS is not configured.
    """
    settings = get_settings()
    log_group = log_group or settings.cloudwatch_log_group
    log_stream = log_stream or settings.cloudwatch_log_stream

    if not log_group:
        logger.debug("cloudwatch.not_configured")
        return []

    try:
        return await asyncio.to_thread(
            _fetch_cloudwatch_sync,
            log_group,
            log_stream,
            window_minutes,
            max_lines,
            settings,
        )
    except Exception as exc:
        logger.warning("cloudwatch.fetch_failed", log_group=log_group, error=str(exc))
        return []


def _fetch_cloudwatch_sync(
    log_group: str,
    log_stream: str | None,
    window_minutes: int,
    max_lines: int,
    settings,
) -> list[str]:
    import boto3

    scrubber = get_scrubber()

    kwargs: dict = {}
    if settings.aws_access_key_id:
        kwargs["aws_access_key_id"] = settings.aws_access_key_id
        kwargs["aws_secret_access_key"] = settings.aws_secret_access_key
    if settings.aws_session_token:
        kwargs["aws_session_token"] = settings.aws_session_token

    client = boto3.client("logs", region_name=settings.aws_region, **kwargs)

    now = datetime.utcnow()
    start_ms = int((now - timedelta(minutes=window_minutes)).timestamp() * 1000)
    end_ms = int(now.timestamp() * 1000)

    if log_stream:
        response = client.get_log_events(
            logGroupName=log_group,
            logStreamName=log_stream,
            startTime=start_ms,
            endTime=end_ms,
            limit=max_lines,
            startFromHead=False,
        )
        events = response.get("events", [])
    else:
        response = client.filter_log_events(
            logGroupName=log_group,
            startTime=start_ms,
            endTime=end_ms,
            limit=max_lines,
        )
        events = response.get("events", [])

    lines = [scrubber.scrub(e.get("message", "")) for e in events if e.get("message")]
    logger.info("cloudwatch.logs_fetched", log_group=log_group, count=len(lines))
    return lines[-max_lines:]
