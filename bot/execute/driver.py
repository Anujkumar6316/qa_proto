"""Execution driver seam — resolve @eN through descriptors, act, assert."""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


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
