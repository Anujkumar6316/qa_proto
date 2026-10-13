"""Crawl service — driver snapshot -> planner_input.json + manifest. Run-relative."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from bot.crawl.annotate import annotate_image
from bot.crawl.normalizer import normalize_snapshot
from bot.events import emit
from bot.ids import new_run_id, relative_ref, safe_join, url_to_slug
from bot.ingest.urls import assert_public_url

DEFAULT_OBJECTIVE = "Single-page crawl: capture planner_input inventory."


def _driver_factory(backend: str, allow_private: bool):
    if backend == "fake":
        from bot.crawl.fake_driver import FakeDriver
        return FakeDriver
    if backend == "playwright":
        from bot.crawl.playwright_driver import PlaywrightDriver
        return PlaywrightDriver
    raise ValueError(f"Unknown crawl backend '{backend}' (expected fake|playwright)")


def run_crawl(
    url: str,
    output_dir: Path,
    *,
    backend: str = "fake",
    scope: str = "all",
    objective: str = DEFAULT_OBJECTIVE,
    run_id: str | None = None,
    allow_private: bool = False,
    driver: Any | None = None,
) -> dict[str, Any]:
    """Crawl one URL -> artifacts/<slug>/pages/<slug>/. Returns the manifest dict."""
    import asyncio

    clean_url = assert_public_url(url, allow_private=allow_private)
    run_id = run_id or new_run_id()
    slug = url_to_slug(clean_url)
    resolved_out = output_dir.resolve()
    crawl_dir = safe_join(resolved_out, slug)
    page_dir = safe_join(crawl_dir, "pages", slug)
    shared_dir = safe_join(page_dir, "shared")
    p1_dir = safe_join(page_dir, "phase_1_crawl")
    shots_dir = safe_join(p1_dir, "screenshots")
    for d in (shared_dir, shots_dir):
        d.mkdir(parents=True, exist_ok=True)

    async def _collect() -> dict[str, Any]:
        drv = driver or _driver_factory(backend, allow_private)()
        try:
            opened = await drv.open(clean_url)
            if not opened.get("ready"):
                raise RuntimeError(f"browser not ready: {opened.get('error', 'unknown')}")
            snap = await drv.snapshot()
            shot_bytes: bytes | None = None
            if hasattr(drv, "screenshot"):
                try:
                    shot_bytes = await drv.screenshot()
                except Exception:
                    shot_bytes = None
            return {"snapshot": snap, "open": opened, "shot": shot_bytes,
                    "backend": getattr(drv, "backend", backend)}
        finally:
            await drv.close()

    result = asyncio.run(_collect())
    snapshot = result["snapshot"]

    planner_input = normalize_snapshot(snapshot, url=clean_url, objective=objective, scope=scope)
    planner_path = safe_join(shared_dir, "planner_input.json")
    planner_path.write_text(json.dumps(planner_input, indent=2), encoding="utf-8")

    # --- Screenshots: raw capture + annotation bound to the snapshot boxes -----
    shot_path = shots_dir / "page.png"
    annotated_path = shots_dir / "page_annotated.png"
    shot_bytes = result.get("shot")
    screenshot_meta: dict[str, Any] = {"captured": False, "annotated": False,
                                       "annotated_components": 0, "total_components": 0}
    if shot_bytes:
        shot_path.write_bytes(shot_bytes)
        components = planner_input["components"]
        ok = annotate_image(shot_bytes, components, annotated_path)
        screenshot_meta = {
            "captured": True,
            "annotated": ok,
            "annotated_components": len(components) if ok else 0,
            "total_components": len(components),
            "coordinate_space": "viewport",
            "source": f"{result['backend']} driver snapshot boxes (ref -> box binding)",
        }

    raw_path = safe_join(p1_dir, "raw_snapshot.json")
    raw_path.write_text(json.dumps(snapshot, indent=2), encoding="utf-8")

    sub_path = safe_join(p1_dir, "sub_urls.txt")
    sub_path.write_text("", encoding="utf-8")

    manifest = {
        "base_url": clean_url,
        "run_id": run_id,
        "total_pages_crawled": 1,
        "backend": result["backend"],
        "deferred_urls_count": 0,
        "deferred_urls_path": relative_ref(resolved_out, sub_path),
        "pages": [{
            "url": clean_url,
            "slug": slug,
            "depth": 0,
            "title": snapshot.get("title", ""),
            "components_count": len(planner_input["components"]),
            "artifacts": {
                "planner_input": relative_ref(resolved_out, planner_path),
                "screenshot": relative_ref(resolved_out, shots_dir / "page_annotated.png"),
                "screenshot_raw": relative_ref(resolved_out, shot_path),
                "raw_snapshot": relative_ref(resolved_out, raw_path),
                "sub_urls": relative_ref(resolved_out, sub_path),
                "phase_1_dir": relative_ref(resolved_out, p1_dir),
                "shared_dir": relative_ref(resolved_out, shared_dir),
            },
            "screenshot": screenshot_meta,
        }],
    }
    manifest_path = safe_join(crawl_dir, "site_manifest.json")
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    emit(page_dir, "crawl", "crawl.completed", {
        "run_id": run_id, "url": clean_url, "scope": scope, "backend": result["backend"],
        "components_count": len(planner_input["components"]),
        "screenshot": screenshot_meta,
    }, artifacts={"planner_input": relative_ref(resolved_out, planner_path),
                  "manifest": relative_ref(resolved_out, manifest_path),
                  "screenshot": relative_ref(resolved_out, annotated_path)})
    return manifest
