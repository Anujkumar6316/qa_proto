"""Shared artifact resolution for API routers. Run-relative, fail-closed, no root imports."""

from __future__ import annotations

import json
from pathlib import Path

from fastapi import HTTPException

from bot.ids import relative_ref, safe_join, validate_slug
from bot.settings import get_settings


def artifacts_root() -> Path:
    return get_settings().resolved_artifacts_dir()


def find_crawl_dir(slug_or_run_id: str) -> Path:
    """Resolve a crawl directory by slug (or 8-hex run_id by scanning manifests)."""
    root = artifacts_root()
    try:
        slug = validate_slug(slug_or_run_id)
        candidate = root / slug
        if (candidate / "site_manifest.json").exists():
            return candidate
    except ValueError:
        pass
    # Fall back to run_id lookup by scanning manifests (bounded).
    if root.exists():
        for d in sorted(root.iterdir()):
            mani = d / "site_manifest.json"
            if d.is_dir() and mani.exists():
                try:
                    if json.loads(mani.read_text(encoding="utf-8")).get("run_id") == slug_or_run_id:
                        return d
                except Exception:
                    continue
    raise HTTPException(404, f"Crawl '{slug_or_run_id}' not found.")


def page_dir_for(slug_or_run_id: str) -> tuple[Path, Path, dict]:
    """Return (crawl_dir, page_dir, manifest). Raises 404 if missing."""
    crawl_dir = find_crawl_dir(slug_or_run_id)
    manifest = json.loads((crawl_dir / "site_manifest.json").read_text(encoding="utf-8"))
    ref = manifest["pages"][0]["artifacts"]["shared_dir"]
    page_dir = (artifacts_root() / ref).resolve()
    if page_dir.name == "shared":
        page_dir = page_dir.parent
    if not page_dir.exists():
        raise HTTPException(404, f"Page directory for '{slug_or_run_id}' not found.")
    return crawl_dir, page_dir, manifest


def load_plan(page_dir: Path) -> dict:
    plan_path = page_dir / "phase_3_plan" / "qa_plan.json"
    if not plan_path.exists():
        raise HTTPException(409, "No plan yet — run POST /plan first.")
    return json.loads(plan_path.read_text(encoding="utf-8"))


def rel(root: Path, target: Path) -> str:
    return relative_ref(root, target)
