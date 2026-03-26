"""
Tests for webhook endpoints.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

# Set env before importing app
os.environ["PAGERDUTY_WEBHOOK_SECRET"] = "test-secret"
os.environ["DEPLOYMENT_MODE"] = "api"
os.environ["ANTHROPIC_API_KEY"] = "sk-ant-test"

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def client(temp_db):
    from main import create_app

    app = create_app()

    with (
        patch("db.init_db", new_callable=AsyncMock),
        patch("ai.client.validate_llm_connection", new_callable=AsyncMock, return_value=True),
    ):
        with TestClient(app, raise_server_exceptions=False) as c:
            yield c


def _make_pd_signature(payload: bytes, secret: str) -> str:
    sig = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
    return f"v1={sig}"


@pytest.fixture
def pd_payload():
    return (FIXTURES_DIR / "sample_pd_alert.json").read_bytes()


@pytest.fixture
def am_payload():
    return (FIXTURES_DIR / "sample_am_alert.json").read_bytes()


# ── PagerDuty ──────────────────────────────────────────────────────────────────

def test_pagerduty_valid_hmac_returns_200(client, pd_payload):
    secret = "test-secret"
    sig = _make_pd_signature(pd_payload, secret)

    with (
        patch("webhook.pagerduty._process_alert", new_callable=AsyncMock),
        patch("db.is_duplicate_webhook", new_callable=AsyncMock, return_value=False),
        patch("db.mark_webhook_processed", new_callable=AsyncMock),
    ):
        response = client.post(
            "/webhooks/pagerduty",
            content=pd_payload,
            headers={
                "Content-Type": "application/json",
                "X-PagerDuty-Signature": sig,
            },
        )

    assert response.status_code == 200
    assert response.json()["status"] == "accepted"


def test_pagerduty_invalid_hmac_returns_403(client, pd_payload):
    bad_sig = "v1=badhash000000000000000000000000000000000000000000000000000000000000"

    response = client.post(
        "/webhooks/pagerduty",
        content=pd_payload,
        headers={
            "Content-Type": "application/json",
            "X-PagerDuty-Signature": bad_sig,
        },
    )

    assert response.status_code == 403


def test_pagerduty_missing_signature_with_secret_returns_403(client, pd_payload, monkeypatch):
    # When a secret is configured, missing sig should fail
    monkeypatch.setenv("PAGERDUTY_WEBHOOK_SECRET", "test-secret")
    from config import get_settings
    get_settings.cache_clear()

    response = client.post(
        "/webhooks/pagerduty",
        content=pd_payload,
        headers={"Content-Type": "application/json"},
    )

    assert response.status_code == 403


def test_pagerduty_deduplication(client, pd_payload):
    secret = "test-secret"
    sig = _make_pd_signature(pd_payload, secret)

    with (
        patch("webhook.pagerduty._process_alert", new_callable=AsyncMock),
        patch("db.is_duplicate_webhook", new_callable=AsyncMock, return_value=True),
        patch("db.mark_webhook_processed", new_callable=AsyncMock),
    ):
        response = client.post(
            "/webhooks/pagerduty",
            content=pd_payload,
            headers={
                "Content-Type": "application/json",
                "X-PagerDuty-Signature": sig,
            },
        )

    assert response.status_code == 200
    # Accepted but not re-processed (deduplicated)


# ── AlertManager ───────────────────────────────────────────────────────────────

def test_alertmanager_valid_token_returns_200(client, am_payload):
    with (
        patch("webhook.alertmanager._process_alert", new_callable=AsyncMock),
        patch("db.is_duplicate_webhook", new_callable=AsyncMock, return_value=False),
        patch("db.mark_webhook_processed", new_callable=AsyncMock),
        # Disable token requirement for this test
        patch("config.get_settings") as mock_settings,
    ):
        from config import Settings
        s = Settings()
        s.pagerduty_webhook_secret = ""  # disable auth for this test
        mock_settings.return_value = s

        response = client.post(
            "/webhooks/alertmanager",
            content=am_payload,
            headers={"Content-Type": "application/json"},
        )

    assert response.status_code == 200


def test_alertmanager_missing_auth_with_secret_returns_401(client, am_payload, monkeypatch):
    monkeypatch.setenv("PAGERDUTY_WEBHOOK_SECRET", "some-am-secret")
    from config import get_settings
    get_settings.cache_clear()

    response = client.post(
        "/webhooks/alertmanager",
        content=am_payload,
        headers={"Content-Type": "application/json"},
        # No Authorization header
    )

    assert response.status_code == 401


def test_alertmanager_wrong_token_returns_403(client, am_payload, monkeypatch):
    monkeypatch.setenv("PAGERDUTY_WEBHOOK_SECRET", "correct-secret")
    from config import get_settings
    get_settings.cache_clear()

    response = client.post(
        "/webhooks/alertmanager",
        content=am_payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": "Bearer wrong-secret",
        },
    )

    assert response.status_code == 403


# ── Health endpoints ───────────────────────────────────────────────────────────

def test_health_endpoint_returns_ok(client):
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "mode" in data
