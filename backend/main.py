"""
SRE Copilot — FastAPI application entry point.

Registers all routers, configures middleware, and handles startup/shutdown.
"""
from __future__ import annotations

import uuid
from contextlib import asynccontextmanager
from typing import AsyncIterator

import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from api.alerts import router as alerts_router
from api.feedback import router as feedback_router
from api.health import router as health_router
from api.runbooks import router as runbooks_router
from webhook.router import router as webhook_router
from ai.client import validate_llm_connection
from config import get_settings
from db import init_db

# ── Structured logging setup ───────────────────────────────────────────────────

def _configure_logging(settings) -> None:
    import logging

    processors = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
    ]

    if settings.is_production:
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer())

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, settings.log_level.upper(), logging.INFO)
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


logger = structlog.get_logger()

# ── Lifespan ───────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    _configure_logging(settings)

    logger.info(
        "startup",
        app=settings.app_name,
        mode=settings.deployment_mode.value,
        env=settings.app_env,
    )

    # Initialize database
    await init_db()

    # Validate LLM connection (non-blocking warning on failure)
    llm_ok = await validate_llm_connection()
    if not llm_ok:
        logger.warning(
            "startup.llm_connection_failed",
            mode=settings.deployment_mode.value,
            hint="Check your API key and network connectivity.",
        )

    yield

    logger.info("shutdown", app=settings.app_name)


# ── App factory ────────────────────────────────────────────────────────────────

def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        docs_url="/docs" if not settings.is_production else None,
        redoc_url=None,
        lifespan=lifespan,
    )

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins_list,
        allow_credentials=True,
        allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
        allow_headers=["*"],
    )

    # Global exception handler — never leak internals to clients
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        request_id = str(uuid.uuid4())
        logger.error(
            "unhandled_exception",
            request_id=request_id,
            path=request.url.path,
            method=request.method,
            error=str(exc),
            exc_info=True,
        )
        return JSONResponse(
            status_code=500,
            content={"error": "Internal server error", "request_id": request_id},
        )

    # Routers
    app.include_router(health_router)
    app.include_router(webhook_router)
    app.include_router(alerts_router)
    app.include_router(feedback_router)
    app.include_router(runbooks_router)

    return app


app = create_app()
