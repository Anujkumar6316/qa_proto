"""Execution driver seam — resolve @eN through descriptors, act, assert."""

from __future__ import annotations

from typing import Any, Final, Protocol, runtime_checkable

# Actions that evaluate state instead of mutating it. Single source of truth:
# the runner, the replayer, and the plan grounding gate all derive from these.
ASSERT_ACTIONS: Final[frozenset[str]] = frozenset({
    "assert_url_contains", "assert_text", "assert_attr", "assert_visible", "assert_hidden",
})

# Mutation actions a plan may contain (mirrors bot.plan.grounding.ACTION_STEPS).
MUTATION_ACTIONS: Final[frozenset[str]] = frozenset({
    "click", "fill", "hover", "press_key", "scroll_into_view", "navigate",
    "select", "check", "uncheck", "scroll",
})

KNOWN_ACTIONS: Final[frozenset[str]] = ASSERT_ACTIONS | MUTATION_ACTIONS


@runtime_checkable
class Resolved(Protocol):
    ok: bool
    selector: str
    visible: bool
    strategy_used: str


@runtime_checkable
class ExecDriver(Protocol):
    """One browser context per case. Callers depend on this, never a backend."""

    async def goto(self, url: str) -> dict[str, Any]:
        """Navigate. Returns {ok, final_url, status, error?}."""
        ...

    async def resolve(self, ref: str) -> dict[str, Any]:
        """Resolve @eN to a unique locator. Returns {ok, selector, visible, strategy_used}."""
        ...

    async def act(self, action: str, resolved: dict[str, Any] | None,
                  value: str | None = None, attribute: str | None = None) -> dict[str, Any]:
        """Perform click/fill/hover/etc. Returns {ok, error?}."""
        ...

    async def page_text(self) -> str:
        ...

    async def current_url(self) -> str:
        ...

    async def close(self) -> None:
        ...


async def evaluate_assert(
    driver: Any, action: str, ref: str | None, value: str | None, attribute: str | None
) -> tuple[bool, str, str | None]:
    """Run one assert action against a driver. Returns (passed, actual, error).

    Shared by the Phase 4 runner and the Phase 5 replayer so replay always
    evaluates assertions exactly the way execution did.
    """
    from bot.execute.assertions import (
        eval_attr, eval_hidden, eval_text_candidates, eval_url_contains, eval_visible,
    )

    if action == "assert_url_contains":
        return eval_url_contains(await driver.current_url(), value or "")
    if action == "assert_text":
        return eval_text_candidates([await driver.page_text()], value or "")
    if action == "assert_attr":
        r = await driver.resolve(ref) if ref else {"ok": False}
        return eval_attr(r.get("attr"), value or "", attribute or "")
    if action == "assert_visible":
        r = await driver.resolve(ref) if ref else {"ok": False, "visible": False}
        return eval_visible(bool(r.get("visible")), ref)
    if action == "assert_hidden":
        r = await driver.resolve(ref) if ref else {"ok": False, "visible": False}
        return eval_hidden(bool(r.get("visible")), ref)
    return False, "", f"unknown assert action '{action}'"


def default_exec_driver_factory(backend: str):
    """Map an execute backend name to its driver class. Fail-closed on unknown."""
    if backend == "fake":
        from bot.execute.fake_driver import FakeExecDriver

        return FakeExecDriver
    raise ValueError(f"Unknown execute backend '{backend}'")
