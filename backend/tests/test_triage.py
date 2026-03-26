"""
Tests for ai/triage.py — mocks the LLM client.
"""
from __future__ import annotations

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from models import Alert, AlertSource, AlertSeverity


def _make_alert(**kwargs) -> Alert:
    defaults = dict(
        source=AlertSource.PAGERDUTY,
        name="High CPU",
        description="CPU usage exceeded 90%",
        service="api-server",
        environment="production",
        fired_at=datetime.utcnow(),
    )
    defaults.update(kwargs)
    return Alert(**defaults)


GOOD_XML_RESPONSE = """
<triage>
  <severity>P2</severity>
  <diagnosis>The API server is experiencing high CPU usage, likely due to a surge in traffic or a runaway process. The primary suspect is the background job processor which was recently deployed.</diagnosis>
  <actions>
    <action>Check running processes: `kubectl top pods -n production`</action>
    <action>Review recent deployments: `kubectl rollout history deployment/api-server -n production`</action>
    <action>If a runaway pod, restart it: `kubectl rollout restart deployment/api-server -n production`</action>
  </actions>
  <escalate_to>Platform team</escalate_to>
  <watch_out>Rolling restart may cause brief 5xx spike — check error rate during rollout.</watch_out>
</triage>
"""

MALFORMED_XML_RESPONSE = """
I cannot parse this properly but here is my analysis:
The CPU usage is high due to memory pressure causing excessive GC cycles.
Steps: 1. Check GC logs 2. Increase heap size 3. Restart service
"""


@pytest.fixture
def mock_llm():
    """Mock the LLM client to return well-formed XML."""
    mock = MagicMock()
    mock.messages.create.return_value = MagicMock(
        content=[MagicMock(text=GOOD_XML_RESPONSE)]
    )
    return mock


@pytest.mark.asyncio
async def test_triage_happy_path(mock_llm, temp_db, temp_chroma):
    with (
        patch("ai.triage.get_llm_client", return_value=mock_llm),
        patch("ai.triage.get_rag_engine") as mock_rag_factory,
    ):
        mock_rag = AsyncMock()
        mock_rag.search_runbooks.return_value = ["Runbook chunk: Check kubectl top pods"]
        mock_rag.search_similar_incidents.return_value = []
        mock_rag.store_incident = AsyncMock()
        mock_rag_factory.return_value = mock_rag

        from ai.triage import triage_alert
        from db import init_db
        await init_db()

        alert = _make_alert()
        result = await triage_alert(alert)

        assert result.alert_id == alert.id
        assert result.severity == AlertSeverity.P2
        assert "CPU" in result.diagnosis or "cpu" in result.diagnosis.lower()
        assert len(result.actions) >= 3
        assert result.escalate_to == "Platform team"
        assert result.watch_out is not None


@pytest.mark.asyncio
async def test_triage_malformed_xml_falls_back(temp_db, temp_chroma):
    mock_llm = MagicMock()
    mock_llm.messages.create.return_value = MagicMock(
        content=[MagicMock(text=MALFORMED_XML_RESPONSE)]
    )

    with (
        patch("ai.triage.get_llm_client", return_value=mock_llm),
        patch("ai.triage.get_rag_engine") as mock_rag_factory,
    ):
        mock_rag = AsyncMock()
        mock_rag.search_runbooks.return_value = []
        mock_rag.search_similar_incidents.return_value = []
        mock_rag.store_incident = AsyncMock()
        mock_rag_factory.return_value = mock_rag

        from ai.triage import triage_alert
        from db import init_db
        await init_db()

        alert = _make_alert()
        result = await triage_alert(alert)

        # Should not raise — must return a TriageResult
        assert result.alert_id == alert.id
        assert result.severity == AlertSeverity.UNKNOWN
        assert len(result.diagnosis) > 0


@pytest.mark.asyncio
async def test_triage_timeout_returns_degraded_result(temp_db, temp_chroma):
    import asyncio

    async def slow_call(*args, **kwargs):
        await asyncio.sleep(100)  # Will be cancelled by timeout

    with (
        patch("ai.triage.get_llm_client"),
        patch("ai.triage._call_llm_with_retry", side_effect=asyncio.TimeoutError()),
        patch("ai.triage.get_rag_engine") as mock_rag_factory,
    ):
        mock_rag = AsyncMock()
        mock_rag.search_runbooks.return_value = []
        mock_rag.search_similar_incidents.return_value = []
        mock_rag_factory.return_value = mock_rag

        from ai.triage import triage_alert
        from db import init_db
        await init_db()

        alert = _make_alert()
        result = await triage_alert(alert)

        assert result.severity == AlertSeverity.UNKNOWN
        assert "timed out" in result.diagnosis.lower()
        assert len(result.actions) > 0


@pytest.mark.asyncio
async def test_triage_scrubs_credentials_before_llm(temp_db, temp_chroma):
    """Verify the scrubber runs before the LLM message is built."""
    captured_messages = []

    def capture_create(*args, **kwargs):
        captured_messages.extend(kwargs.get("messages", []))
        return MagicMock(content=[MagicMock(text=GOOD_XML_RESPONSE)])

    mock_llm = MagicMock()
    mock_llm.messages.create.side_effect = capture_create

    with (
        patch("ai.triage.get_llm_client", return_value=mock_llm),
        patch("ai.triage.get_rag_engine") as mock_rag_factory,
    ):
        mock_rag = AsyncMock()
        mock_rag.search_runbooks.return_value = []
        mock_rag.search_similar_incidents.return_value = []
        mock_rag.store_incident = AsyncMock()
        mock_rag_factory.return_value = mock_rag

        from ai.triage import triage_alert
        from db import init_db
        await init_db()

        alert = _make_alert(
            raw_payload={"db_url": "postgres://admin:secretpassword@prod-db:5432/app"}
        )
        log_lines = ["password=hunter2", "normal log line", "api_key=sk-ant-supersecret123456"]

        await triage_alert(alert, log_lines=log_lines)

        # Check that the captured messages don't contain credentials
        all_message_content = " ".join(
            m.get("content", "") for m in captured_messages if isinstance(m.get("content"), str)
        )
        assert "secretpassword" not in all_message_content
        assert "hunter2" not in all_message_content


@pytest.mark.asyncio
async def test_triage_with_log_context(mock_llm, temp_db, temp_chroma):
    with (
        patch("ai.triage.get_llm_client", return_value=mock_llm),
        patch("ai.triage.get_rag_engine") as mock_rag_factory,
    ):
        mock_rag = AsyncMock()
        mock_rag.search_runbooks.return_value = []
        mock_rag.search_similar_incidents.return_value = []
        mock_rag.store_incident = AsyncMock()
        mock_rag_factory.return_value = mock_rag

        from ai.triage import triage_alert
        from db import init_db
        await init_db()

        alert = _make_alert()
        logs = ["ERROR: OOM kill", "INFO: restarting", "ERROR: still failing"]

        result = await triage_alert(alert, log_lines=logs)
        assert result is not None


@pytest.mark.asyncio
async def test_triage_rag_failure_does_not_crash(temp_db, temp_chroma):
    """If RAG fails, triage should continue without context."""
    mock_llm = MagicMock()
    mock_llm.messages.create.return_value = MagicMock(
        content=[MagicMock(text=GOOD_XML_RESPONSE)]
    )

    with (
        patch("ai.triage.get_llm_client", return_value=mock_llm),
        patch("ai.triage.get_rag_engine") as mock_rag_factory,
    ):
        mock_rag = AsyncMock()
        mock_rag.search_runbooks.side_effect = Exception("ChromaDB unavailable")
        mock_rag.search_similar_incidents.side_effect = Exception("ChromaDB unavailable")
        mock_rag_factory.return_value = mock_rag

        from ai.triage import triage_alert
        from db import init_db
        await init_db()

        alert = _make_alert()
        result = await triage_alert(alert)
        assert result is not None
