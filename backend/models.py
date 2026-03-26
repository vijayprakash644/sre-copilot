"""
Pydantic v2 models for SRE Copilot.
These are the canonical data shapes used throughout the application.
"""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field
import uuid


class AlertSeverity(str, Enum):
    P1 = "P1"
    P2 = "P2"
    P3 = "P3"
    UNKNOWN = "UNKNOWN"


class AlertSource(str, Enum):
    PAGERDUTY = "pagerduty"
    ALERTMANAGER = "alertmanager"
    DATADOG = "datadog"
    MANUAL = "manual"


class Alert(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    source: AlertSource
    name: str
    description: str
    service: str | None = None
    environment: str | None = None
    labels: dict[str, str] = Field(default_factory=dict)
    annotations: dict[str, str] = Field(default_factory=dict)
    fired_at: datetime = Field(default_factory=datetime.utcnow)
    raw_payload: dict = Field(default_factory=dict)


class TriageResult(BaseModel):
    alert_id: str
    severity: AlertSeverity
    diagnosis: str
    actions: list[str]
    escalate_to: str | None = None
    watch_out: str | None = None
    runbook_sources: list[str] = Field(default_factory=list)
    past_incident_refs: list[str] = Field(default_factory=list)
    llm_model: str
    deployment_mode: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    feedback: str | None = None


class RunbookDocument(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    filename: str
    content_type: str  # "markdown" | "pdf"
    chunk_count: int
    ingested_at: datetime = Field(default_factory=datetime.utcnow)


class FeedbackRequest(BaseModel):
    alert_id: str
    rating: Literal["good", "bad"]
    comment: str | None = None


class AlertWithTriage(BaseModel):
    alert: Alert
    triage: TriageResult | None = None


class AlertStats(BaseModel):
    total_alerts: int
    p1_count: int
    p2_count: int
    p3_count: int
    feedback_good_rate: float


class HealthStatus(BaseModel):
    status: str
    mode: str


class ReadyStatus(BaseModel):
    status: str
    db: str
    llm: str
