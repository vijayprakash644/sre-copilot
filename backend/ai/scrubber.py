"""
Log and data scrubber.

MUST run before any log data is stored in ChromaDB, sent to any LLM API,
or included in any external request. No exceptions.

Design principles:
- Conservative: prefer false positives (redact too much) over false negatives
- Auditable: all patterns are explicit regex, no ML-based detection
- Fast: pure regex, no external calls, runs in microseconds per line
- Configurable: customer-specific patterns can be appended at runtime
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass
class _Pattern:
    name: str
    regex: re.Pattern[str]
    replacement: str


_DEFAULT_PATTERNS: list[tuple[str, str, str]] = [
    # Email addresses
    (
        "email",
        r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}",
        "[REDACTED_EMAIL]",
    ),
    # JWT tokens (three base64 segments separated by dots)
    (
        "jwt",
        r"eyJ[A-Za-z0-9_\-]+\.eyJ[A-Za-z0-9_\-]+\.[A-Za-z0-9_\-]+",
        "[REDACTED_JWT]",
    ),
    # Bearer tokens in Authorization headers
    (
        "bearer_token",
        r"(?i)(bearer\s+)[A-Za-z0-9\-._~+/]+=*",
        r"\1[REDACTED_TOKEN]",
    ),
    # Slack tokens (xoxb-, xoxp-, xoxa-, xoxs-, xapp-)
    (
        "slack_token",
        r"xox[bpas]-[0-9A-Za-z\-]+",
        "[REDACTED_SLACK_TOKEN]",
    ),
    # AWS access key IDs
    (
        "aws_access_key",
        r"(?<![A-Z0-9])AKIA[0-9A-Z]{16}(?![A-Z0-9])",
        "[REDACTED_AWS_KEY]",
    ),
    # Anthropic API keys
    (
        "anthropic_key",
        r"sk-ant-[A-Za-z0-9\-_]{20,}",
        "[REDACTED_ANTHROPIC_KEY]",
    ),
    # OpenAI / generic sk- keys (must come after anthropic to avoid double-match)
    (
        "openai_key",
        r"sk-[A-Za-z0-9]{20,}",
        "[REDACTED_API_KEY]",
    ),
    # GitHub personal access tokens (classic: ghp_, gho_, github_pat_)
    (
        "github_token",
        r"(?:ghp_|gho_|github_pat_)[A-Za-z0-9_]{20,}",
        "[REDACTED_GITHUB_TOKEN]",
    ),
    # Passwords/secrets in key=value or key: value format
    (
        "password_kv",
        r"(?i)(?:password|passwd|secret|api_key|apikey|token|credential|auth)(\s*[=:]\s*)(?:\"[^\"]*\"|'[^']*'|[^\s,;&\"']+)",
        r"[REDACTED_CREDENTIAL]\1[REDACTED]",
    ),
    # DB connection strings (postgres://, mysql://, mongodb://, redis://)
    (
        "db_connection_string",
        r"(?i)(?:postgres(?:ql)?|mysql|mongodb|redis|amqp)://[^@\s]+@[^\s]+",
        "[REDACTED_CONNECTION_STRING]",
    ),
    # Private IP ranges: 10.x.x.x, 172.16-31.x.x, 192.168.x.x
    # Note: port suffixes like :8080 are preserved — we only redact the IP part
    (
        "private_ip_10",
        r"(?<!\d)10\.\d{1,3}\.\d{1,3}\.\d{1,3}(?!\d)",
        "[REDACTED_PRIVATE_IP]",
    ),
    (
        "private_ip_172",
        r"(?<!\d)172\.(?:1[6-9]|2\d|3[01])\.\d{1,3}\.\d{1,3}(?!\d)",
        "[REDACTED_PRIVATE_IP]",
    ),
    (
        "private_ip_192",
        r"(?<!\d)192\.168\.\d{1,3}\.\d{1,3}(?!\d)",
        "[REDACTED_PRIVATE_IP]",
    ),
    # Public IPv4 addresses (rough heuristic — comes after private ranges)
    (
        "public_ip",
        r"(?<!\d)(?!0\.)(?!127\.)(?!255\.)(?:[1-9]\d?|1\d{2}|2[0-4]\d|25[0-4])"
        r"\.(?:\d{1,3})\.(?:\d{1,3})\.(?:\d{1,3})(?!\d)(?!:\d)",
        "[REDACTED_IP]",
    ),
    # Credit card numbers (Luhn-checkable pattern: 13-19 digits with optional spaces/dashes)
    (
        "credit_card",
        r"(?<!\d)(?:4[0-9]{12}(?:[0-9]{3})?|5[1-5][0-9]{14}|3[47][0-9]{13}"
        r"|3(?:0[0-5]|[68][0-9])[0-9]{11}|6(?:011|5[0-9]{2})[0-9]{12}"
        r"|(?:2131|1800|35\d{3})\d{11})(?!\d)",
        "[REDACTED_CARD]",
    ),
]


class LogScrubber:
    """
    Scrubs sensitive data from log lines and arbitrary strings.
    Thread-safe (read-only after init), suitable as a singleton.
    """

    def __init__(self) -> None:
        self._patterns: list[_Pattern] = []
        for name, pattern, replacement in _DEFAULT_PATTERNS:
            self._patterns.append(
                _Pattern(
                    name=name,
                    regex=re.compile(pattern),
                    replacement=replacement,
                )
            )

    def add_pattern(self, name: str, pattern: str, replacement: str = "[REDACTED]") -> None:
        """Add a customer-specific scrubbing pattern at runtime."""
        self._patterns.append(
            _Pattern(
                name=name,
                regex=re.compile(pattern),
                replacement=replacement,
            )
        )

    def scrub(self, text: str) -> str:
        """Scrub all sensitive patterns from a single string."""
        if not text:
            return text
        for p in self._patterns:
            text = p.regex.sub(p.replacement, text)
        return text

    def scrub_lines(self, lines: list[str], max_lines: int = 20) -> list[str]:
        """
        Scrub a list of log lines, capping to max_lines (taking the last N).
        Returns the scrubbed, truncated list.
        """
        if not lines:
            return []
        # Take the last max_lines (most recent)
        truncated = lines[-max_lines:] if len(lines) > max_lines else lines
        return [self.scrub(line) for line in truncated]

    def scrub_dict(self, data: dict) -> dict:
        """Recursively scrub all string values in a dictionary."""
        result: dict = {}
        for key, value in data.items():
            if isinstance(value, str):
                result[key] = self.scrub(value)
            elif isinstance(value, dict):
                result[key] = self.scrub_dict(value)
            elif isinstance(value, list):
                result[key] = [
                    self.scrub(item) if isinstance(item, str) else item
                    for item in value
                ]
            else:
                result[key] = value
        return result


_scrubber_instance: LogScrubber | None = None


def get_scrubber() -> LogScrubber:
    """Return the application-level scrubber singleton."""
    global _scrubber_instance
    if _scrubber_instance is None:
        _scrubber_instance = LogScrubber()
    return _scrubber_instance
