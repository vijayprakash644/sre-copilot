"""
LLM client factory.

Returns the appropriate client based on DEPLOYMENT_MODE env var.
This is the ONLY place in the codebase that knows which LLM is in use.
All other code calls get_llm_client() and uses the returned client identically.
"""
from __future__ import annotations

import asyncio
from typing import Any

import anthropic
import httpx
import structlog

from config import DeploymentMode, get_settings

logger = structlog.get_logger()

_client_instance: Any = None


def get_llm_client() -> Any:
    """
    Mode: api     → anthropic.Anthropic(api_key=...)
    Mode: bedrock → anthropic.AnthropicBedrock(aws_region=..., ...)
    Mode: ollama  → OllamaClient (httpx-based, OpenAI-compatible API)
    """
    global _client_instance
    if _client_instance is not None:
        return _client_instance

    settings = get_settings()
    mode = settings.deployment_mode

    if mode == DeploymentMode.api:
        _client_instance = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        logger.info("llm.client_created", mode="api", model=settings.anthropic_model)

    elif mode == DeploymentMode.bedrock:
        kwargs: dict[str, Any] = {"aws_region": settings.aws_region}
        if settings.aws_access_key_id:
            kwargs["aws_access_key"] = settings.aws_access_key_id
        if settings.aws_secret_access_key:
            kwargs["aws_secret_key"] = settings.aws_secret_access_key
        if settings.aws_session_token:
            kwargs["aws_session_token"] = settings.aws_session_token
        _client_instance = anthropic.AnthropicBedrock(**kwargs)
        logger.info("llm.client_created", mode="bedrock", region=settings.aws_region)

    elif mode == DeploymentMode.ollama:
        _client_instance = OllamaClient(
            base_url=settings.ollama_base_url,
            model=settings.ollama_model,
        )
        logger.info("llm.client_created", mode="ollama", model=settings.ollama_model)

    else:
        raise ValueError(f"Unknown deployment mode: {mode}")

    return _client_instance


def reset_llm_client() -> None:
    """Reset client singleton — useful for testing."""
    global _client_instance
    _client_instance = None


def get_model_name() -> str:
    """Return the model identifier for the current deployment mode."""
    settings = get_settings()
    mode = settings.deployment_mode
    if mode == DeploymentMode.api:
        return settings.anthropic_model
    elif mode == DeploymentMode.bedrock:
        return settings.bedrock_model
    elif mode == DeploymentMode.ollama:
        return settings.ollama_model
    return "unknown"


async def validate_llm_connection() -> bool:
    """
    Make a minimal test call to verify LLM connectivity on startup.
    Returns True if successful, False otherwise.
    """
    settings = get_settings()
    mode = settings.deployment_mode

    try:
        if mode == DeploymentMode.ollama:
            client = get_llm_client()
            result = await client.complete("Say 'ok'", max_tokens=5)
            ok = bool(result)
        else:
            client = get_llm_client()
            model = get_model_name()
            # Use asyncio.to_thread since the Anthropic SDK is synchronous
            response = await asyncio.to_thread(
                lambda: client.messages.create(
                    model=model,
                    max_tokens=5,
                    messages=[{"role": "user", "content": "Say 'ok'"}],
                )
            )
            ok = len(response.content) > 0

        logger.info("llm.connection_validated", mode=mode.value, ok=ok)
        return ok

    except Exception as exc:
        logger.warning("llm.connection_failed", mode=mode.value, error=str(exc))
        return False


class OllamaClient:
    """
    Thin wrapper around Ollama's OpenAI-compatible HTTP API.
    Provides a messages.create()-compatible interface.
    """

    def __init__(self, base_url: str, model: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self._http = httpx.AsyncClient(timeout=60.0)

    async def complete(self, prompt: str, max_tokens: int = 1024) -> str:
        response = await self._http.post(
            f"{self.base_url}/api/generate",
            json={"model": self.model, "prompt": prompt, "stream": False},
        )
        response.raise_for_status()
        return response.json().get("response", "")

    class _Messages:
        def __init__(self, client: "OllamaClient") -> None:
            self._client = client

        async def create(
            self,
            model: str,
            max_tokens: int,
            messages: list[dict],
            system: str | None = None,
        ) -> "_OllamaResponse":
            # Build prompt from messages list
            parts = []
            if system:
                parts.append(f"System: {system}\n")
            for msg in messages:
                role = msg.get("role", "user")
                content = msg.get("content", "")
                parts.append(f"{role.capitalize()}: {content}")
            prompt = "\n".join(parts)

            text = await self._client.complete(prompt, max_tokens=max_tokens)
            return _OllamaResponse(text=text)

    @property
    def messages(self) -> "_Messages":
        return self._Messages(self)


class _OllamaResponse:
    """Minimal response wrapper matching Anthropic SDK shape."""

    def __init__(self, text: str) -> None:
        self.content = [type("Block", (), {"text": text})()]
