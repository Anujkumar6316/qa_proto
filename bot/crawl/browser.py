"""BrowserDriver seam — one Protocol, no backend leaks into callers."""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class PageSnapshot(Protocol):
    url: str
    title: str
    components: list[dict[str, Any]]


@runtime_checkable
class BrowserDriver(Protocol):
    """All pipeline code depends on this. No backend leaks into callers."""

    async def open(self, url: str, *, viewport: tuple[int, int] | None = None) -> dict[str, Any]:
        """Navigate to url. Returns {ready, final_url, status, error?}."""
        ...

    async def snapshot(self) -> dict[str, Any]:
        """Return {url, title, components: [{ref, role, name, box, ...}]}."""
        ...

    async def close(self) -> None:
        """Release the session. Must be idempotent and safe in finally blocks."""
        ...
