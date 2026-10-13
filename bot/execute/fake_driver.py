"""FakeExecDriver — deterministic offline execution for contract tests."""

from __future__ import annotations

from typing import Any


class FakeExecDriver:
    """Scripted DOM: refs resolve, clicks may navigate, fills set values, asserts read state."""

    backend = "fake"

    def __init__(self, *, url: str = "https://example.com/login",
                 visible_refs: set[str] | None = None,
                 text: str = "Welcome", attrs: dict[str, str] | None = None,
                 nav_map: dict[str, str] | None = None) -> None:
        self._url = url
        self._visible = visible_refs if visible_refs is not None else {"@e1", "@e2"}
        self._text = text
        self._attrs = attrs or {}
        self._nav_map = nav_map or {}
        self._closed = 0

    async def goto(self, url: str) -> dict[str, Any]:
        self._url = url
        return {"ok": True, "final_url": url, "status": 200}

    async def resolve(self, ref: str) -> dict[str, Any]:
        ok = ref in self._visible
        return {"ok": ok, "selector": f"[data-ref='{ref}']",
                "visible": ok, "strategy_used": "fake" if ok else "none"}

    async def act(self, action: str, resolved: dict[str, Any] | None,
                  value: str | None = None, attribute: str | None = None) -> dict[str, Any]:
        if action in ("click",) and resolved is not None:
            ref = (resolved.get("selector") or "").split("'")[1] if resolved.get("selector") else ""
            if ref in self._nav_map:
                self._url = self._nav_map[ref]
        if action == "fill" and attribute:
            self._attrs[attribute] = value or ""
        if action in ("navigate",) and value:
            self._url = value
        return {"ok": True}

    async def page_text(self) -> str:
        return self._text

    async def current_url(self) -> str:
        return self._url

    async def close(self) -> None:
        self._closed += 1
