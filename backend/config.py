"""
Application settings loaded from environment variables via pydantic-settings.
All configuration lives here — import get_settings() everywhere.
"""
from __future__ import annotations

from enum import Enum
from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class DeploymentMode(str, Enum):
    api = "api"
    bedrock = "bedrock"
    ollama = "ollama"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Deployment
    deployment_mode: DeploymentMode = DeploymentMode.api

    # Anthropic API
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-4-6-20250514-1"

    # AWS Bedrock
    aws_region: str = "us-east-1"
    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""
    aws_session_token: str = ""
    bedrock_model: str = "anthropic.claude-sonnet-4-6-20250514-v1:0"

    # Ollama
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.1:8b"

    # Slack
    slack_bot_token: str = ""
    slack_signing_secret: str = ""
    slack_app_token: str = ""
    incidents_channel: str = "#incidents"

    # PagerDuty
    pagerduty_webhook_secret: str = ""

    # Datadog
    datadog_api_key: str = ""
    datadog_app_key: str = ""
    datadog_site: str = "datadoghq.com"

    # CloudWatch
    cloudwatch_log_group: str = ""
    cloudwatch_log_stream: str = ""

    # Storage
    chroma_persist_dir: str = "./data/chroma"
    database_url: str = "./data/sre_copilot.db"
    data_dir: str = "./data"

    # API security
    api_secret_key: str = Field(default="", alias="API_SECRET_KEY")
    allowed_origins: str = "http://localhost:3000"

    # App
    app_name: str = "SRE Copilot"
    app_env: Literal["development", "production"] = "development"
    log_level: str = "INFO"
    max_log_lines: int = 20
    max_runbook_chunks: int = 3
    max_past_incidents: int = 2
    triage_timeout_seconds: int = 15

    @property
    def allowed_origins_list(self) -> list[str]:
        return [o.strip() for o in self.allowed_origins.split(",") if o.strip()]

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
