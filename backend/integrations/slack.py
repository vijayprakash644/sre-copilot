"""
Slack integration.
Uses slack-bolt async mode.

Two responsibilities:
1. post_triage_message(channel, alert, triage_result) — formats and posts Block Kit message
2. Bolt app with slash command /sre-ask and button action handlers
"""
from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

import structlog

from config import get_settings
from models import Alert, AlertSeverity, TriageResult

if TYPE_CHECKING:
    pass

logger = structlog.get_logger()

_slack_app = None


def get_slack_app():
    """Return the Slack Bolt app singleton."""
    global _slack_app
    if _slack_app is not None:
        return _slack_app

    settings = get_settings()
    if not settings.slack_bot_token:
        return None

    from slack_bolt.async_app import AsyncApp

    _slack_app = AsyncApp(
        token=settings.slack_bot_token,
        signing_secret=settings.slack_signing_secret,
    )

    _register_handlers(_slack_app)
    return _slack_app


def _register_handlers(app) -> None:
    """Register all Bolt action and slash command handlers."""

    @app.action("resolved")
    async def handle_resolved(ack, body, client):
        await ack()
        user = body.get("user", {}).get("name", "someone")
        alert_id = body.get("actions", [{}])[0].get("value", "")
        channel = body.get("container", {}).get("channel_id", "")
        ts = body.get("container", {}).get("message_ts", "")

        from db import update_triage_feedback
        await update_triage_feedback(alert_id, "good")

        if channel and ts:
            await client.chat_postMessage(
                channel=channel,
                thread_ts=ts,
                text=f"✓ Resolved by @{user}",
            )

    @app.action("wrong_diagnosis")
    async def handle_wrong_diagnosis(ack, body, client):
        await ack()
        alert_id = body.get("actions", [{}])[0].get("value", "")
        channel = body.get("container", {}).get("channel_id", "")
        ts = body.get("container", {}).get("message_ts", "")

        from db import update_triage_feedback
        await update_triage_feedback(alert_id, "bad")

        if channel and ts:
            await client.chat_postMessage(
                channel=channel,
                thread_ts=ts,
                text="Thanks, noted. This feedback improves future triage.",
            )

    @app.action("escalate")
    async def handle_escalate(ack, body, client):
        await ack()
        channel = body.get("container", {}).get("channel_id", "")
        ts = body.get("container", {}).get("message_ts", "")
        user = body.get("user", {}).get("name", "someone")

        if channel and ts:
            await client.chat_postMessage(
                channel=channel,
                thread_ts=ts,
                text=f"🚨 Escalated by @{user} — please review this incident.",
            )

    @app.action("ask_followup")
    async def handle_ask_followup(ack, body, client, payload):
        await ack()
        trigger_id = body.get("trigger_id", "")
        alert_id = body.get("actions", [{}])[0].get("value", "")

        if trigger_id:
            await client.views_open(
                trigger_id=trigger_id,
                view={
                    "type": "modal",
                    "callback_id": "followup_modal",
                    "private_metadata": alert_id,
                    "title": {"type": "plain_text", "text": "Ask a follow-up"},
                    "submit": {"type": "plain_text", "text": "Ask"},
                    "blocks": [
                        {
                            "type": "input",
                            "block_id": "question",
                            "label": {"type": "plain_text", "text": "Your question"},
                            "element": {
                                "type": "plain_text_input",
                                "action_id": "question_input",
                                "multiline": True,
                                "placeholder": {
                                    "type": "plain_text",
                                    "text": "e.g. What does this error mean in context of our Redis setup?",
                                },
                            },
                        }
                    ],
                },
            )

    @app.view("followup_modal")
    async def handle_followup_submit(ack, body, client, view):
        await ack()
        question = view["state"]["values"]["question"]["question_input"]["value"]
        alert_id = view.get("private_metadata", "")
        channel = get_settings().incidents_channel

        asyncio.create_task(_answer_followup(client, channel, alert_id, question))

    @app.command("/sre-ask")
    async def handle_sre_ask(ack, body, client):
        await ack()
        question = body.get("text", "")
        channel = body.get("channel_id", get_settings().incidents_channel)

        if not question:
            await client.chat_postMessage(
                channel=channel,
                text="Please provide a question. Usage: `/sre-ask <your question>`",
            )
            return

        asyncio.create_task(_answer_followup(client, channel, "", question))


async def _answer_followup(client, channel: str, alert_id: str, question: str) -> None:
    """Answer a follow-up question using RAG context."""
    from ai.rag import get_rag_engine
    from ai.client import get_llm_client, get_model_name
    from ai.prompts import SYSTEM_PROMPT
    from ai.scrubber import get_scrubber

    scrubber = get_scrubber()
    question = scrubber.scrub(question)

    rag = get_rag_engine()
    chunks = await rag.search_runbooks(question, n_results=3)

    context = "\n\n".join(chunks) if chunks else "(no runbook context)"
    prompt = (
        f"Engineer follow-up question: {question}\n\n"
        f"Relevant runbook context:\n{context}\n\n"
        f"Answer concisely and practically."
    )

    try:
        import anthropic
        from ai.client import get_llm_client, get_model_name
        import asyncio as _asyncio

        llm = get_llm_client()
        model = get_model_name()
        response = await _asyncio.to_thread(
            lambda: llm.messages.create(
                model=model,
                max_tokens=512,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": prompt}],
            )
        )
        answer = response.content[0].text
    except Exception as exc:
        logger.error("slack.followup_failed", error=str(exc))
        answer = "Sorry, I couldn't generate an answer. Please check the logs."

    await client.chat_postMessage(channel=channel, text=answer)


# ── Message formatting ─────────────────────────────────────────────────────────

_SEVERITY_EMOJI = {
    AlertSeverity.P1: "🔴",
    AlertSeverity.P2: "🟠",
    AlertSeverity.P3: "🟡",
    AlertSeverity.UNKNOWN: "⚪",
}


def _format_actions_for_slack(actions: list[str]) -> str:
    lines = []
    for i, action in enumerate(actions, 1):
        # Wrap shell commands in code format
        if "`" in action or action.strip().startswith(("kubectl", "docker", "curl", "aws", "psql", "redis")):
            lines.append(f"{i}. {action}")
        else:
            lines.append(f"{i}. {action}")
    return "\n".join(lines)


def build_triage_blocks(alert: Alert, triage: TriageResult) -> list[dict]:
    """Build Slack Block Kit blocks for a triage result."""
    emoji = _SEVERITY_EMOJI.get(triage.severity, "⚪")
    service_str = f" | {alert.service}" if alert.service else ""
    fired_str = alert.fired_at.strftime("%Y-%m-%d %H:%M UTC")

    actions_text = _format_actions_for_slack(triage.actions)

    context_parts = []
    if triage.runbook_sources:
        context_parts.append(f"Runbooks: {', '.join(triage.runbook_sources[:2])}")
    if triage.past_incident_refs:
        context_parts.append(f"Similar: {', '.join(triage.past_incident_refs[:2])}")
    context_parts.append(f"Fired: {fired_str}")
    context_str = " | ".join(context_parts)

    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f"{emoji} [{triage.severity.value}] {alert.name}{service_str}",
            },
        },
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"*Diagnosis*\n{triage.diagnosis}"},
        },
        {"type": "divider"},
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"*Immediate Actions*\n{actions_text}"},
        },
    ]

    if triage.watch_out:
        blocks.append(
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"⚠️ *Watch out:* {triage.watch_out}",
                },
            }
        )

    if triage.escalate_to:
        blocks.append(
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"📣 *Escalate to:* {triage.escalate_to}",
                },
            }
        )

    blocks.append(
        {
            "type": "context",
            "elements": [{"type": "mrkdwn", "text": context_str}],
        }
    )

    blocks.append(
        {
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "Resolved ✓"},
                    "style": "primary",
                    "action_id": "resolved",
                    "value": alert.id,
                },
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "Escalate"},
                    "style": "danger",
                    "action_id": "escalate",
                    "value": alert.id,
                },
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "Wrong diagnosis"},
                    "action_id": "wrong_diagnosis",
                    "value": alert.id,
                },
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "Ask follow-up"},
                    "action_id": "ask_followup",
                    "value": alert.id,
                },
            ],
        }
    )

    return blocks


async def post_triage_message(channel: str, alert: Alert, triage: TriageResult) -> None:
    """Post the triage result to Slack. Fails gracefully if Slack is not configured."""
    settings = get_settings()
    if not settings.slack_bot_token:
        logger.info("slack.not_configured_skipping_post")
        return

    app = get_slack_app()
    if not app:
        return

    try:
        blocks = build_triage_blocks(alert, triage)
        text = f"[{triage.severity.value}] {alert.name} — {triage.diagnosis[:100]}"
        await app.client.chat_postMessage(
            channel=channel,
            blocks=blocks,
            text=text,  # fallback for notifications
        )
        logger.info("slack.message_posted", alert_id=alert.id, channel=channel)
    except Exception as exc:
        logger.error("slack.post_failed", alert_id=alert.id, error=str(exc))
