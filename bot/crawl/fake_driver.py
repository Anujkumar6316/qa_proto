"""FakeDriver — deterministic, offline. Runs the same contract tests as real drivers."""

from __future__ import annotations

from typing import Any


class FakeDriver:
    """In-memory driver for unit and contract tests. No browser, no network."""

    backend = "fake"
    driver_version = "0.2.0"

    def __init__(self, snapshot: dict[str, Any] | None = None, *, ready: bool = True,
                 screenshot: bytes | None = None) -> None:
        self._snapshot = snapshot or {
            "url": "https://example.com/", "title": "Example",
            "components": [
                {"ref": "@e1", "role": "textbox", "name": "Email", "box": [10, 20, 300, 44]},
                {"ref": "@e2", "role": "button", "name": "Submit", "box": [10, 60, 120, 88]},
            ],
        }
        self._ready = ready
        if screenshot is not None:
            self._screenshot = screenshot
        else:
            from PIL import Image
            import io
            buf = io.BytesIO()
            Image.new("RGB", (1280, 900), (255, 255, 255)).save(buf, format="PNG")
            self._screenshot = buf.getvalue()
        self.opened = 0
        self.closed = 0

    async def open(self, url: str, *, viewport: tuple[int, int] | None = None) -> dict[str, Any]:
        self.opened += 1
        self._snapshot.setdefault("url", url)
        return {"ready": self._ready, "final_url": self._snapshot.get("url", url), "status": 200}

    async def snapshot(self) -> dict[str, Any]:
        return dict(self._snapshot)

    async def screenshot(self) -> bytes:
        """Deterministic blank-viewport PNG so annotation runs in tests too."""
        return self._screenshot

    async def close(self) -> None:
        self.closed += 1
