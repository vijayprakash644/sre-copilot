"""
Embedding helpers.
Uses Anthropic's voyage-3 embeddings via the Anthropic API.
Falls back to a simple hash-based stub when the API key is not configured (for tests).
"""
from __future__ import annotations

import asyncio
import hashlib
import struct

import structlog

from config import get_settings

logger = structlog.get_logger()


async def embed_texts(texts: list[str]) -> list[list[float]]:
    """
    Embed a list of texts and return their embedding vectors.
    Uses voyage-3 via the Anthropic SDK when configured; falls back to stub otherwise.
    """
    settings = get_settings()

    if not settings.anthropic_api_key:
        logger.warning("embeddings.no_api_key_using_stub")
        return [_stub_embedding(t) for t in texts]

    try:
        import anthropic

        client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        response = await asyncio.to_thread(
            lambda: client.embeddings.create(
                model="voyage-3",
                input=texts,
            )
        )
        return [item.embedding for item in response.data]
    except Exception as exc:
        logger.warning("embeddings.api_failed_using_stub", error=str(exc))
        return [_stub_embedding(t) for t in texts]


async def embed_text(text: str) -> list[float]:
    """Embed a single text string."""
    results = await embed_texts([text])
    return results[0]


def _stub_embedding(text: str, dim: int = 1024) -> list[float]:
    """
    Deterministic stub embedding for testing / no-API scenarios.
    Not semantically meaningful but consistent for the same input.
    """
    digest = hashlib.sha256(text.encode()).digest()
    floats = []
    for i in range(0, min(len(digest), dim * 4), 4):
        chunk = digest[i : i + 4]
        if len(chunk) < 4:
            chunk = chunk + b"\x00" * (4 - len(chunk))
        val = struct.unpack(">f", chunk)[0]
        if not (val != val):  # exclude NaN
            floats.append(val)
    # Pad or truncate to dim
    while len(floats) < dim:
        floats.extend(floats or [0.0])
    return floats[:dim]
