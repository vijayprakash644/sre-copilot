"""
Runbook management API.

POST /api/runbooks/upload — upload a PDF or Markdown runbook
GET  /api/runbooks         — list ingested runbooks
DELETE /api/runbooks/{id}  — remove a runbook

Auth: X-API-Key header must match API_SECRET_KEY env var.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from pathlib import Path

import structlog
from fastapi import APIRouter, Depends, File, Header, HTTPException, UploadFile

from ai.rag import get_rag_engine
from config import get_settings
from db import save_runbook_document, get_runbook_documents, delete_runbook_document
from models import RunbookDocument

logger = structlog.get_logger()

router = APIRouter(prefix="/api/runbooks", tags=["runbooks"])


def _require_api_key(x_api_key: str = Header(default="")) -> None:
    settings = get_settings()
    if not settings.api_secret_key:
        return  # Skip auth if key not configured (dev mode)
    if x_api_key != settings.api_secret_key:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")


@router.post("/upload", response_model=RunbookDocument, dependencies=[Depends(_require_api_key)])
async def upload_runbook(file: UploadFile = File(...)) -> RunbookDocument:
    filename = file.filename or "unknown"
    suffix = Path(filename).suffix.lower()

    if suffix not in (".md", ".pdf"):
        raise HTTPException(
            status_code=400,
            detail="Only .md and .pdf files are supported",
        )

    settings = get_settings()
    upload_dir = Path(settings.data_dir) / "uploads"
    upload_dir.mkdir(parents=True, exist_ok=True)

    doc_id = str(uuid.uuid4())
    dest = upload_dir / f"{doc_id}{suffix}"

    content = await file.read()
    dest.write_bytes(content)

    try:
        rag = get_rag_engine()
        doc = await rag.ingest_document(dest, doc_id)
        await save_runbook_document(doc_id, filename, doc.content_type, doc.chunk_count)
        logger.info("runbooks.uploaded", doc_id=doc_id, filename=filename)
        return doc
    except Exception as exc:
        dest.unlink(missing_ok=True)
        logger.error("runbooks.upload_failed", filename=filename, error=str(exc))
        raise HTTPException(status_code=500, detail="Failed to ingest runbook")


@router.get("", response_model=list[RunbookDocument], dependencies=[Depends(_require_api_key)])
async def list_runbooks() -> list[RunbookDocument]:
    rows = await get_runbook_documents()
    return [
        RunbookDocument(
            id=r["id"],
            filename=r["filename"],
            content_type=r["content_type"],
            chunk_count=r["chunk_count"],
            ingested_at=datetime.fromisoformat(r["ingested_at"]),
        )
        for r in rows
    ]


@router.delete("/{doc_id}", dependencies=[Depends(_require_api_key)])
async def remove_runbook(doc_id: str) -> dict:
    rag = get_rag_engine()
    await rag.delete_document(doc_id)
    deleted = await delete_runbook_document(doc_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Runbook not found")
    return {"status": "deleted", "doc_id": doc_id}
