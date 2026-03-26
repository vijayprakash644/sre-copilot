"""
Main triage orchestration.

Order of operations:
1. Scrub alert payload
2. Scrub log_lines if provided
3. Fetch runbook chunks from RAG
4. Fetch similar past incidents from RAG
5. Build user message
6. Call LLM with timeout
7. Parse XML response into TriageResult
8. Store incident in ChromaDB
9. Return TriageResult
"""
from __future__ import annotations

import asyncio
import time
import xml.etree.ElementTree as ET
from datetime import datetime

import structlog
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from ai.client import get_llm_client, get_model_name
from ai.prompts import SYSTEM_PROMPT, build_user_message
from ai.rag import get_rag_engine
from ai.scrubber import get_scrubber
from config import get_settings, DeploymentMode
from models import Alert, AlertSeverity, TriageResult

logger = structlog.get_logger()


async def triage_alert(
    alert: Alert,
    log_lines: list[str] | None = None,
) -> TriageResult:
    """
    Main triage orchestration. Never raises — returns a degraded result on failure.
    """
    start = time.monotonic()
    settings = get_settings()
    scrubber = get_scrubber()

    # 1. Scrub alert raw_payload
    alert.raw_payload = scrubber.scrub_dict(alert.raw_payload)

    # 2. Scrub log lines
    scrubbed_logs: list[str] = []
    if log_lines:
        scrubbed_logs = scrubber.scrub_lines(log_lines, max_lines=settings.max_log_lines)

    # 3 & 4. Fetch RAG context concurrently
    rag = get_rag_engine()
    query = f"{alert.name} {alert.description} {alert.service or ''}"

    try:
        runbook_chunks, past_incidents = await asyncio.gather(
            rag.search_runbooks(query, n_results=settings.max_runbook_chunks),
            rag.search_similar_incidents(alert, n_results=settings.max_past_incidents),
        )
    except Exception as exc:
        logger.warning("triage.rag_fetch_failed", error=str(exc), alert_id=alert.id)
        runbook_chunks, past_incidents = [], []

    # 5. Build user message
    user_message = build_user_message(
        alert=alert,
        log_lines=scrubbed_logs,
        runbook_chunks=runbook_chunks,
        past_incidents=past_incidents,
    )

    # 6. Call LLM
    try:
        raw_response = await asyncio.wait_for(
            _call_llm_with_retry(user_message),
            timeout=settings.triage_timeout_seconds,
        )
    except asyncio.TimeoutError:
        logger.error("triage.timeout", alert_id=alert.id, timeout=settings.triage_timeout_seconds)
        return _timeout_result(alert, settings.deployment_mode.value, get_model_name())
    except Exception as exc:
        logger.error("triage.llm_error", alert_id=alert.id, error=str(exc))
        return _error_result(alert, settings.deployment_mode.value, get_model_name(), str(exc))

    # 7. Parse XML response
    result = _parse_triage_response(
        raw=raw_response,
        alert=alert,
        runbook_chunks=runbook_chunks,
        past_incidents=past_incidents,
        model=get_model_name(),
        deployment_mode=settings.deployment_mode.value,
    )

    duration_ms = int((time.monotonic() - start) * 1000)
    logger.info(
        "triage.completed",
        alert_id=alert.id,
        severity=result.severity.value,
        duration_ms=duration_ms,
        deployment_mode=settings.deployment_mode.value,
    )

    # 8. Store incident in RAG (fire-and-forget, don't block)
    asyncio.create_task(_store_incident_safe(alert, result))

    return result


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=8),
    retry=retry_if_exception_type(Exception),
    reraise=True,
)
async def _call_llm_with_retry(user_message: str) -> str:
    """Call the LLM with automatic retry on transient errors."""
    settings = get_settings()
    client = get_llm_client()
    model = get_model_name()

    if settings.deployment_mode == DeploymentMode.ollama:
        response = await client.messages.create(
            model=model,
            max_tokens=1024,
            messages=[{"role": "user", "content": user_message}],
            system=SYSTEM_PROMPT,
        )
    else:
        response = await asyncio.to_thread(
            lambda: client.messages.create(
                model=model,
                max_tokens=1024,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user_message}],
            )
        )

    return response.content[0].text


def _parse_triage_response(
    raw: str,
    alert: Alert,
    runbook_chunks: list[str],
    past_incidents: list[str],
    model: str,
    deployment_mode: str,
) -> TriageResult:
    """Parse the LLM XML response into a TriageResult. Falls back gracefully."""
    try:
        return _parse_xml(raw, alert, runbook_chunks, past_incidents, model, deployment_mode)
    except Exception as exc:
        logger.warning("triage.xml_parse_failed", error=str(exc), alert_id=alert.id)
        return _parse_plaintext_fallback(raw, alert, runbook_chunks, model, deployment_mode)


def _parse_xml(
    raw: str,
    alert: Alert,
    runbook_chunks: list[str],
    past_incidents: list[str],
    model: str,
    deployment_mode: str,
) -> TriageResult:
    # Extract <triage>...</triage> block (may have surrounding text)
    start = raw.find("<triage>")
    end = raw.find("</triage>")
    if start == -1 or end == -1:
        raise ValueError("No <triage> block found")

    xml_str = raw[start : end + len("</triage>")]
    root = ET.fromstring(xml_str)

    def get_text(tag: str) -> str:
        el = root.find(tag)
        return el.text.strip() if el is not None and el.text else ""

    severity_str = get_text("severity").upper()
    try:
        severity = AlertSeverity(severity_str)
    except ValueError:
        severity = AlertSeverity.UNKNOWN

    actions_el = root.find("actions")
    actions = []
    if actions_el is not None:
        for action_el in actions_el.findall("action"):
            text = action_el.text.strip() if action_el.text else ""
            if text:
                actions.append(text)

    # Build runbook sources from chunk filenames
    runbook_sources = [f"runbook_chunk_{i+1}" for i in range(len(runbook_chunks))]
    past_refs = [f"incident_{i+1}" for i in range(len(past_incidents))]

    return TriageResult(
        alert_id=alert.id,
        severity=severity,
        diagnosis=get_text("diagnosis"),
        actions=actions or ["Review the alert details and check service logs manually."],
        escalate_to=get_text("escalate_to") or None,
        watch_out=get_text("watch_out") or None,
        runbook_sources=runbook_sources,
        past_incident_refs=past_refs,
        llm_model=model,
        deployment_mode=deployment_mode,
        created_at=datetime.utcnow(),
    )


def _parse_plaintext_fallback(
    raw: str,
    alert: Alert,
    runbook_chunks: list[str],
    model: str,
    deployment_mode: str,
) -> TriageResult:
    """Last-resort parser: treat the entire response as the diagnosis."""
    return TriageResult(
        alert_id=alert.id,
        severity=AlertSeverity.UNKNOWN,
        diagnosis=raw[:500] if raw else "Unable to parse triage response.",
        actions=["Review the raw LLM response in the alert detail.", "Escalate if uncertain."],
        runbook_sources=[f"runbook_chunk_{i+1}" for i in range(len(runbook_chunks))],
        llm_model=model,
        deployment_mode=deployment_mode,
        created_at=datetime.utcnow(),
    )


def _timeout_result(alert: Alert, deployment_mode: str, model: str) -> TriageResult:
    return TriageResult(
        alert_id=alert.id,
        severity=AlertSeverity.UNKNOWN,
        diagnosis="Triage timed out — check logs manually. The LLM did not respond in time.",
        actions=[
            "Check service logs directly in your log aggregation system.",
            "Review recent deployments that may have introduced regressions.",
            "Escalate to on-call lead if the issue is P1/P2.",
        ],
        llm_model=model,
        deployment_mode=deployment_mode,
        created_at=datetime.utcnow(),
    )


def _error_result(alert: Alert, deployment_mode: str, model: str, error: str) -> TriageResult:
    return TriageResult(
        alert_id=alert.id,
        severity=AlertSeverity.UNKNOWN,
        diagnosis=f"Triage failed due to an internal error. Manual review required.",
        actions=[
            "Check service logs directly in your log aggregation system.",
            "Escalate to on-call lead if the issue appears severe.",
        ],
        llm_model=model,
        deployment_mode=deployment_mode,
        created_at=datetime.utcnow(),
    )


async def _store_incident_safe(alert: Alert, result: TriageResult) -> None:
    try:
        await get_rag_engine().store_incident(alert, result)
    except Exception as exc:
        logger.warning("triage.store_incident_failed", alert_id=alert.id, error=str(exc))
