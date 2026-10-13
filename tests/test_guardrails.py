"""Guardrail tests — selector bypass, external nav, sandbox, budget."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from bot.execute.guardrails import (  # noqa: E402
    evaluate_action, is_domain_allowed, validate_step_budget,
)

_DOMAINS = {"example.com"}


def test_destructive_keyword_blocked() -> None:
    ok, reason = evaluate_action("click", target_name="Delete account", target_role="button")
    assert not ok and "destructive" in reason


def test_selector_bypass_caught() -> None:
    ok, _ = evaluate_action("click", target_selector="button#checkout-pay")
    assert not ok


def test_sandbox_allows_destructive_but_not_external() -> None:
    ok, _ = evaluate_action("click", target_name="Delete", sandbox_mode=True)
    assert ok
    ok2, why = evaluate_action("click", target_name="Delete", target_href="https://evil.com/x",
                               allowed_domains=_DOMAINS, sandbox_mode=True)
    assert not ok2 and "external navigation" in why


def test_navigate_external_blocked() -> None:
    ok, _ = evaluate_action("navigate", value="https://evil.com/x", allowed_domains=_DOMAINS)
    assert not ok
    ok2, _ = evaluate_action("navigate", value="https://shop.example.com/x", allowed_domains=_DOMAINS)
    assert ok2


def test_domain_matching() -> None:
    assert is_domain_allowed("https://shop.example.com/p", _DOMAINS)
    assert not is_domain_allowed("https://notexample.com/p", _DOMAINS)
    assert is_domain_allowed("/relative", _DOMAINS)
    assert is_domain_allowed("https://x.com", [])


def test_step_budget() -> None:
    ok, _ = validate_step_budget([1, 2, 3], max_steps=6)
    assert ok
    bad, why = validate_step_budget(list(range(7)), max_steps=6)
    assert not bad and "exceeds budget" in why
