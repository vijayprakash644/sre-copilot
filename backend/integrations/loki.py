"""
Grafana Loki client (optional).
Fetches log lines from Loki for triage context enrichment.
"""
from __future__ import annotations

from datetime import datetime, timedelta

import httpx
import structlog

from ai.scrubber import get_scrubber

logger = structlog.get_logger()


async def fetch_logs(
    loki_url: str,
    query: str,
    window_minutes: int = 30,
    max_lines: int = 20,
) -> list[str]:
    """
    Fetch recent logs from Grafana Loki.
    query: LogQL query string, e.g. '{app="my-service"}'
    Returns empty list if loki_url not provided.
    """
    if not loki_url:
        return []

    scrubber = get_scrubber()
    now = datetime.utcnow()
    start_ns = int((now - timedelta(minutes=window_minutes)).timestamp() * 1e9)
    end_ns = int(now.timestamp() * 1e9)

    params = {
        "query": query,
        "start": str(start_ns),
        "end": str(end_ns),
        "limit": str(max_lines),
        "direction": "backward",
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"{loki_url.rstrip('/')}/loki/api/v1/query_range",
                params=params,
            )
            response.raise_for_status()

        data = response.json()
        lines = []
        for stream in data.get("data", {}).get("result", []):
            for _ts, line in stream.get("values", []):
                lines.append(scrubber.scrub(line))

        logger.info("loki.logs_fetched", query=query, count=len(lines))
        return lines[-max_lines:]

    except Exception as exc:
        logger.warning("loki.fetch_failed", error=str(exc))
        return []
