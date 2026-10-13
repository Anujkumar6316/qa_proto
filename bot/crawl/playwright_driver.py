"""PlaywrightDriver — Playwright-native backend. Import is lazy (dep is optional)."""

from __future__ import annotations

from typing import Any

backend = "playwright"


class PlaywrightDriver:
    """One browser per run, one context per crawl. Fresh context, no purge needed."""

    backend = "playwright"
    driver_version = "playwright-async"

    def __init__(self, *, headless: bool = True, action_timeout_ms: int = 5000,
                 nav_timeout_ms: int = 30000, ignore_https_errors: bool = False) -> None:
        self._headless = headless
        self._action_timeout_ms = action_timeout_ms
        self._nav_timeout_ms = nav_timeout_ms
        self._ignore_https_errors = ignore_https_errors
        self._playwright = None
        self._browser = None
        self._context = None
        self._page = None

    async def _ensure_started(self) -> None:
        if self._page is not None:
            return
        from playwright.async_api import async_playwright  # lazy import

        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(headless=self._headless)
        self._context = await self._browser.new_context(
            ignore_https_errors=self._ignore_https_errors,
            viewport={"width": 1280, "height": 900},
        )
        self._context.set_default_timeout(self._action_timeout_ms)
        self._page = await self._context.new_page()
        self._page.set_default_navigation_timeout(self._nav_timeout_ms)

    async def open(self, url: str, *, viewport: tuple[int, int] | None = None) -> dict[str, Any]:
        await self._ensure_started()
        try:
            resp = await self._page.goto(url, wait_until="domcontentloaded")
            status = resp.status if resp else 0
            final_url = self._page.url
            title = await self._page.title()
            return {"ready": True, "final_url": final_url, "status": status, "title": title}
        except Exception as exc:
            return {"ready": False, "final_url": "", "status": 0, "error": str(exc)}

    async def snapshot(self) -> dict[str, Any]:
        if self._page is None:
            raise RuntimeError("snapshot() called before open()")
        url = self._page.url
        title = await self._page.title()
        components = await self._collect_components()
        return {"url": url, "title": title, "components": components}

    async def _collect_components(self) -> list[dict[str, Any]]:
        """Interactive elements with boxes + stable selector fingerprints."""
        script = r"""
        () => {
            const sel = 'a[href], button, input:not([type=hidden]), select, textarea, [role=button], [role=link], [role=textbox], [role=checkbox]';
            const out = [];
            document.querySelectorAll(sel).forEach((el, i) => {
                const r = el.getBoundingClientRect();
                const role = el.getAttribute('role') || el.tagName.toLowerCase();
                const name = (el.getAttribute('aria-label') || el.innerText || el.getAttribute('placeholder') || el.name || el.value || '').trim().slice(0, 120);
                const type = el.getAttribute('type') || '';
                let fingerprint = '';
                try {
                    const path = [];
                    let node = el;
                    while (node && node !== document.body && path.length < 4) {
                        let part = node.tagName.toLowerCase();
                        if (node.id) { part += '#' + node.id; path.unshift(part); break; }
                        const cls = (node.className || '').toString().trim().split(/\s+/).filter(Boolean).slice(0, 2).join('.');
                        if (cls) part += '.' + cls;
                        path.unshift(part);
                        node = node.parentElement;
                    }
                    fingerprint = path.join(' > ');
                } catch (e) {}
                out.push({
                    ref: '@e' + (i + 1),
                    role: role,
                    name: name || '(unnamed)',
                    box: [Math.round(r.x), Math.round(r.y), Math.round(r.x + r.width), Math.round(r.y + r.height)],
                    type: type,
                    fingerprint: fingerprint,
                    visible_in_folds: [1],
                });
            });
            return out;
        }
        """
        return await self._page.evaluate(script)

    async def close(self) -> None:
        for closer in (self._context, self._browser):
            try:
                if closer is not None:
                    await closer.close()
            except Exception:
                pass
        try:
            if self._playwright is not None:
                await self._playwright.stop()
        except Exception:
            pass
        self._page = self._context = self._browser = self._playwright = None

    async def __aenter__(self) -> PlaywrightDriver:
        return self

    async def __aexit__(self, *exc: object) -> None:
        await self.close()
