"""Execute guardrails — blast-radius boundaries. Pure, fail-closed.

Prototype note: the destructive-action sandbox gate has been REMOVED — all
actions run by default. The domain allowlist (external-navigation boundary)
stays because it protects against crawling off-site, not against user intent.
"""

from __future__ import annotations

import re
from typing import Any
from urllib.parse import urlparse

DESTRUCTIVE_KEYWORDS: frozenset[str] = frozenset({
    "delete", "remove", "destroy", "drop", "purge", "checkout", "pay",
    "purchase", "buy", "place order", "submit order", "transfer", "charge",
    "terminate", "unsubscribe", "order now", "place your order",
})
_DESTRUCTIVE_RE = re.compile(r"\b(" + "|".join(re.escape(k) for k in DESTRUCTIVE_KEYWORDS) + r")\b", re.IGNORECASE)


def is_destructive(action: str, *, target_name: str = "", target_role: str | None = None,
                   value: str | None = None, target_selector: str | None = None) -> bool:
    """Informational only (tagging/reporting). No longer blocks execution."""
    combined = f"{action} {target_name} {target_role or ''} {value or ''} {target_selector or ''}"
    return _DESTRUCTIVE_RE.search(combined) is not None


def is_domain_allowed(url: str, allowed_domains: set[str] | list[str]) -> bool:
    if not url or not allowed_domains:
        return True
    try:
        netloc = urlparse(url).netloc.lower()
        if not netloc:
            return True
        host = netloc.split(":")[0]
        for d in allowed_domains:
            clean = d.split(":")[0].lower()
            if host == clean or host.endswith(f".{clean}"):
                return True
        return False
    except Exception:
        return False


def evaluate_action(
    action: str,
    *,
    target_name: str = "",
    target_role: str | None = None,
    value: str | None = None,
    target_href: str | None = None,
    target_selector: str | None = None,
    allowed_domains: set[str] | list[str] | None = None,
) -> tuple[bool, str | None]:
    """Return (is_allowed, reason). Only the external-navigation boundary blocks.

    The destructive-action gate was removed for the prototype: actions matching
    DESTRUCTIVE_KEYWORDS are allowed by default (use `is_destructive` to tag
    them for reporting if needed).
    """
    if target_href and action in ("click", "hover"):
        href = target_href.strip()
        if href.startswith(("http://", "https://")) and not is_domain_allowed(href, allowed_domains or set()):
            return False, f"external navigation blocked: href '{href}' is outside allowed domains — assert href instead"

    if action == "navigate":
        nav = (value or target_href or "").strip()
        if nav.startswith(("http://", "https://")) and not is_domain_allowed(nav, allowed_domains or set()):
            return False, f"external navigation blocked: destination '{nav}' outside allowed domains"

    return True, None


def validate_step_budget(steps: list[Any], max_steps: int = 6) -> tuple[bool, str | None]:
    if len(steps) > max_steps:
        return False, f"Step count ({len(steps)}) exceeds budget ({max_steps})"
    return True, None
