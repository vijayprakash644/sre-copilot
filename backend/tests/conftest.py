"""
Pytest configuration and shared fixtures.
"""
from __future__ import annotations

import os
import tempfile

import pytest
import pytest_asyncio

# Set test environment before importing app modules
os.environ.setdefault("DEPLOYMENT_MODE", "api")
os.environ.setdefault("ANTHROPIC_API_KEY", "sk-ant-test-key-for-testing-only")
os.environ.setdefault("ANTHROPIC_MODEL", "claude-sonnet-4-6-20250514-1")
os.environ.setdefault("API_SECRET_KEY", "test-secret-key")
os.environ.setdefault("PAGERDUTY_WEBHOOK_SECRET", "test-pd-secret")
os.environ.setdefault("SLACK_BOT_TOKEN", "")
os.environ.setdefault("APP_ENV", "development")


@pytest.fixture
def temp_db(tmp_path, monkeypatch):
    """Provide a temporary database for each test."""
    db_path = str(tmp_path / "test.db")
    monkeypatch.setenv("DATABASE_URL", db_path)
    # Reset settings cache
    from config import get_settings
    get_settings.cache_clear()
    return db_path


@pytest.fixture
def temp_chroma(tmp_path, monkeypatch):
    """Provide a temporary ChromaDB directory."""
    chroma_path = str(tmp_path / "chroma")
    monkeypatch.setenv("CHROMA_PERSIST_DIR", chroma_path)
    from config import get_settings
    get_settings.cache_clear()
    # Reset RAG singleton
    import ai.rag as rag_module
    rag_module._rag_instance = None
    return chroma_path


@pytest.fixture(autouse=True)
def reset_settings_cache():
    """Reset settings LRU cache between tests to pick up monkeypatched env vars."""
    from config import get_settings
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture(autouse=True)
def reset_llm_client():
    """Reset LLM client singleton between tests."""
    import ai.client as client_module
    client_module._client_instance = None
    yield
    client_module._client_instance = None
