"""Replayer — re-run a candidate in a fresh session to prove reproducibility.

Deterministic: unknown actions raise. A candidate is 'reproduced' only when the
terminal assertion fails again in the replay. No LLM.
"""

from __future__ import annotations

import asyncio
from typing import Any

from bot.execute.assertions import (
    eval_attr, eval_hidden, eval_text_candidates, eval_url_contains, eval_visible,
)
from bot.execute.runner import _driver_factory, _evaluate_assert

ASSERT_ACTIONS = frozenset({
    "assert_url_contains", "assert_text", "assert_attr", "assert_visible", "assert_hidden",
})
KNOWN_ACTIONS = ASSERT_ACTIONS | frozenset({
    "click", "fill", "hover", "press_key", "navigate", "scroll_into_view",
    "select", "check", "uncheck", "scroll",
})


async def _replay_one(driver: Any, target_url: str, steps: list[dict[str, Any]]) -> tuple[bool, str]:
    opened = await driver.goto(target_url)
    if not opened.get("ok"):
        raise RuntimeError(f"replay navigation failed: {opened.get('error', '')}")
    last_assert_error = ""
    for step in steps:
        action = step.get("action")
        if action not in KNOWN_ACTIONS:
            raise ValueError(f"replay: unknown action '{action}'")
        if action in ASSERT_ACTIONS:
            passed, _actual, err = await _evaluate_assert(
                driver, action, step.get("target_ref"), step.get("value"), step.get("attribute"))
            if not passed:
                last_assert_error = err or "assertion failed"
        else:
            ref = step.get("target_ref")
            resolved = await driver.resolve(ref) if ref else None
            await driver.act(action, resolved, value=step.get("value"), attribute=step.get("attribute"))
    return bool(last_assert_error), last_assert_error


def replay_candidate(candidate: dict[str, Any], test_case: dict[str, Any], *,
                     target_url: str, backend: str = "fake") -> tuple[bool, str]:
    """Return (reproduced, error). reproduced=True iff the terminal assert fails again."""
    driver_cls = _driver_factory(backend)

    async def _run() -> tuple[bool, str]:
        driver = driver_cls()
        try:
            return await _replay_one(driver, target_url, test_case.get("steps", []))
        finally:
            await driver.close()

    return asyncio.run(_run())
