"""
System prompt and user message builder for SRE triage.

All inputs to build_user_message() MUST already be scrubbed before calling.
XML structure is used for reliable, parseable output.
"""
from __future__ import annotations

from models import Alert

SYSTEM_PROMPT = """You are an expert Site Reliability Engineer on-call assistant. \
Your role is to rapidly triage production incidents and provide clear, actionable guidance.

When given an alert, recent logs, relevant runbook excerpts, and similar past incidents, \
you produce a structured triage response that helps engineers resolve issues quickly — \
even at 3am with minimal context.

## Output format (required)

Respond with ONLY the following XML structure. No preamble, no markdown, no explanation outside the tags.

<triage>
  <severity>P1|P2|P3|UNKNOWN</severity>
  <diagnosis>2-3 sentence plain-language explanation of what is likely happening and why. \
Be specific: name the probable root cause, affected component, and likely impact.</diagnosis>
  <actions>
    <action>First immediate action (most urgent first). If it is a shell command, wrap it in backticks.</action>
    <action>Second action</action>
    <action>Third action (add more as needed, typically 3-5 total)</action>
  </actions>
  <escalate_to>Team or person to escalate to if this is not resolved in 15 minutes. \
Leave empty if the engineer should be able to resolve it solo.</escalate_to>
  <watch_out>Common pitfall or gotcha specific to this type of incident. \
Leave empty if none applies.</watch_out>
</triage>

## Severity guide
- P1: Service down, data loss in progress, revenue impact, SLA breach imminent
- P2: Significant degradation, partial outage, elevated error rate >1%, latency >2x baseline
- P3: Minor issue, no user impact yet, pre-emptive warning
- UNKNOWN: Insufficient information to assess severity

## Principles
- Be direct and specific. Avoid generic advice like "check the logs" — point to what to look for.
- If you reference a command, it must be runnable copy-paste (no placeholders like <your-value>).
- If past incidents are provided and this looks similar, reference what worked before.
- If runbooks are provided, cite which runbook section informed your recommendation.
- Never speculate beyond what the data supports. If uncertain, say so in the diagnosis.
"""


def build_user_message(
    alert: Alert,
    log_lines: list[str],
    runbook_chunks: list[str],
    past_incidents: list[str],
) -> str:
    """
    Build the full XML-structured user message.
    All inputs must already be scrubbed before this function is called.
    """
    # Alert section
    labels_str = "\n".join(f"  {k}: {v}" for k, v in alert.labels.items()) or "  (none)"
    annotations_str = "\n".join(f"  {k}: {v}" for k, v in alert.annotations.items()) or "  (none)"

    alert_block = f"""<alert>
  <name>{_escape_xml(alert.name)}</name>
  <source>{alert.source.value}</source>
  <description>{_escape_xml(alert.description)}</description>
  <service>{_escape_xml(alert.service or 'unknown')}</service>
  <environment>{_escape_xml(alert.environment or 'unknown')}</environment>
  <fired_at>{alert.fired_at.isoformat()}</fired_at>
  <labels>
{labels_str}
  </labels>
  <annotations>
{annotations_str}
  </annotations>
</alert>"""

    # Recent logs section
    if log_lines:
        logs_content = "\n".join(log_lines)
        logs_block = f"<recent_logs>\n{logs_content}\n</recent_logs>"
    else:
        logs_block = "<recent_logs>(no log context available)</recent_logs>"

    # Runbooks section
    if runbook_chunks:
        runbook_parts = "\n\n".join(
            f"<chunk index=\"{i+1}\">\n{chunk}\n</chunk>"
            for i, chunk in enumerate(runbook_chunks)
        )
        runbooks_block = f"<runbooks>\n{runbook_parts}\n</runbooks>"
    else:
        runbooks_block = "<runbooks>(no runbook context available)</runbooks>"

    # Past incidents section
    if past_incidents:
        incident_parts = "\n\n".join(
            f"<incident index=\"{i+1}\">\n{inc}\n</incident>"
            for i, inc in enumerate(past_incidents)
        )
        past_block = f"<past_incidents>\n{incident_parts}\n</past_incidents>"
    else:
        past_block = "<past_incidents>(no similar past incidents found)</past_incidents>"

    return f"""{alert_block}

{logs_block}

{runbooks_block}

{past_block}

Triage this alert now."""


def _escape_xml(text: str) -> str:
    """Minimal XML escaping for text content."""
    return (
        text
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace("\"", "&quot;")
    )
