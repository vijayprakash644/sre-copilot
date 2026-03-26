"""
RAG engine using ChromaDB for runbook and past-incident retrieval.

All text stored in ChromaDB is pre-scrubbed via get_scrubber().scrub().
Supports .md and .pdf source documents.
"""
from __future__ import annotations

import asyncio
import os
from datetime import datetime
from pathlib import Path

import structlog

from ai.embeddings import embed_texts, embed_text
from ai.scrubber import get_scrubber
from config import get_settings
from models import Alert, RunbookDocument, TriageResult

logger = structlog.get_logger()

# Chunking constants
CHUNK_TOKENS = 512
CHUNK_OVERLAP_TOKENS = 50
# Approximate chars per token
CHARS_PER_TOKEN = 4
CHUNK_SIZE = CHUNK_TOKENS * CHARS_PER_TOKEN
OVERLAP_SIZE = CHUNK_OVERLAP_TOKENS * CHARS_PER_TOKEN


class RAGEngine:
    """
    Manages two ChromaDB collections:
      - runbooks: indexed runbook document chunks
      - past_incidents: stored incident + triage summaries
    """

    def __init__(self) -> None:
        self._runbooks_collection = None
        self._incidents_collection = None
        self._initialized = False

    async def _ensure_initialized(self) -> None:
        if self._initialized:
            return
        await asyncio.to_thread(self._init_chroma)
        self._initialized = True

    def _init_chroma(self) -> None:
        import chromadb

        settings = get_settings()
        os.makedirs(settings.chroma_persist_dir, exist_ok=True)

        client = chromadb.PersistentClient(path=settings.chroma_persist_dir)
        self._runbooks_collection = client.get_or_create_collection(
            name="runbooks",
            metadata={"hnsw:space": "cosine"},
        )
        self._incidents_collection = client.get_or_create_collection(
            name="past_incidents",
            metadata={"hnsw:space": "cosine"},
        )
        logger.info("rag.chroma_initialized", path=settings.chroma_persist_dir)

    # ── Document ingestion ─────────────────────────────────────────────────────

    async def ingest_document(self, filepath: Path, doc_id: str) -> RunbookDocument:
        """
        Chunk, embed, and store a runbook document (.md or .pdf).
        All text is scrubbed before embedding/storage.
        """
        await self._ensure_initialized()
        scrubber = get_scrubber()

        suffix = filepath.suffix.lower()
        if suffix == ".pdf":
            text = await asyncio.to_thread(self._extract_pdf, filepath)
            content_type = "pdf"
        else:
            text = filepath.read_text(encoding="utf-8", errors="replace")
            content_type = "markdown"

        text = scrubber.scrub(text)
        chunks = _chunk_text(text, CHUNK_SIZE, OVERLAP_SIZE)

        if not chunks:
            chunks = [text[:CHUNK_SIZE]] if text else ["(empty document)"]

        # Build IDs and embed
        chunk_ids = [f"{doc_id}_chunk_{i}" for i in range(len(chunks))]
        embeddings = await embed_texts(chunks)

        metadatas = [
            {
                "doc_id": doc_id,
                "filename": filepath.name,
                "chunk_index": i,
                "content_type": content_type,
            }
            for i in range(len(chunks))
        ]

        await asyncio.to_thread(
            self._runbooks_collection.upsert,
            ids=chunk_ids,
            documents=chunks,
            embeddings=embeddings,
            metadatas=metadatas,
        )

        logger.info(
            "rag.document_ingested",
            doc_id=doc_id,
            filename=filepath.name,
            chunks=len(chunks),
        )

        return RunbookDocument(
            id=doc_id,
            filename=filepath.name,
            content_type=content_type,
            chunk_count=len(chunks),
            ingested_at=datetime.utcnow(),
        )

    @staticmethod
    def _extract_pdf(filepath: Path) -> str:
        from pypdf import PdfReader

        reader = PdfReader(str(filepath))
        pages = []
        for page in reader.pages:
            text = page.extract_text()
            if text:
                pages.append(text)
        return "\n\n".join(pages)

    async def delete_document(self, doc_id: str) -> None:
        """Remove all chunks for a document from the runbooks collection."""
        await self._ensure_initialized()

        results = await asyncio.to_thread(
            self._runbooks_collection.get,
            where={"doc_id": doc_id},
        )
        ids_to_delete = results.get("ids", [])
        if ids_to_delete:
            await asyncio.to_thread(
                self._runbooks_collection.delete,
                ids=ids_to_delete,
            )
        logger.info("rag.document_deleted", doc_id=doc_id, chunks_removed=len(ids_to_delete))

    # ── Runbook search ─────────────────────────────────────────────────────────

    async def search_runbooks(self, query: str, n_results: int = 3) -> list[str]:
        """
        Semantic search over ingested runbook chunks.
        Returns a list of relevant text chunks (already scrubbed).
        """
        await self._ensure_initialized()
        scrubber = get_scrubber()
        query = scrubber.scrub(query)

        try:
            query_embedding = await embed_text(query)
            results = await asyncio.to_thread(
                self._runbooks_collection.query,
                query_embeddings=[query_embedding],
                n_results=min(n_results, max(1, self._runbooks_collection.count())),
                include=["documents"],
            )
            docs = results.get("documents", [[]])[0]
            return docs
        except Exception as exc:
            logger.warning("rag.search_runbooks_failed", error=str(exc))
            return []

    # ── Past incidents ─────────────────────────────────────────────────────────

    async def store_incident(self, alert: Alert, triage: TriageResult) -> None:
        """Embed and store a completed incident + triage for future retrieval."""
        await self._ensure_initialized()
        scrubber = get_scrubber()

        summary = (
            f"Alert: {alert.name}\n"
            f"Service: {alert.service or 'unknown'}\n"
            f"Description: {alert.description}\n"
            f"Severity: {triage.severity.value}\n"
            f"Diagnosis: {triage.diagnosis}\n"
            f"Actions taken: {'; '.join(triage.actions)}\n"
        )
        summary = scrubber.scrub(summary)
        embedding = await embed_text(summary)

        metadata = {
            "alert_id": alert.id,
            "alert_name": alert.name,
            "service": alert.service or "",
            "severity": triage.severity.value,
            "fired_at": alert.fired_at.isoformat(),
        }

        await asyncio.to_thread(
            self._incidents_collection.upsert,
            ids=[alert.id],
            documents=[summary],
            embeddings=[embedding],
            metadatas=[metadata],
        )
        logger.info("rag.incident_stored", alert_id=alert.id)

    async def search_similar_incidents(
        self, alert: Alert, n_results: int = 2
    ) -> list[str]:
        """Retrieve similar past incidents for context."""
        await self._ensure_initialized()
        scrubber = get_scrubber()

        query = scrubber.scrub(f"{alert.name} {alert.description} {alert.service or ''}")

        try:
            count = await asyncio.to_thread(self._incidents_collection.count)
            if count == 0:
                return []

            query_embedding = await embed_text(query)
            results = await asyncio.to_thread(
                self._incidents_collection.query,
                query_embeddings=[query_embedding],
                n_results=min(n_results, count),
                include=["documents"],
            )
            docs = results.get("documents", [[]])[0]
            return docs
        except Exception as exc:
            logger.warning("rag.search_incidents_failed", error=str(exc))
            return []


def _chunk_text(text: str, chunk_size: int, overlap: int) -> list[str]:
    """Split text into overlapping chunks."""
    if not text:
        return []
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= len(text):
            break
        start = end - overlap
    return chunks


_rag_instance: RAGEngine | None = None


def get_rag_engine() -> RAGEngine:
    """Return the application-level RAG engine singleton."""
    global _rag_instance
    if _rag_instance is None:
        _rag_instance = RAGEngine()
    return _rag_instance
