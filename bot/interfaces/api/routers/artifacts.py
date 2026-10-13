"""Artifacts router — screenshots, folds, planner_input, sub_urls, manifest map."""

from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, PlainTextResponse

from bot.ids import safe_join
from bot.interfaces.api.resolve import artifacts_root, page_dir_for, rel

router = APIRouter(prefix="/artifacts", tags=["Artifacts"])


def _planner_input(page_dir: Path) -> Path:
    for candidate in ("shared/planner_input.json", "phase_1_crawl/planner_input.json", "planner_input.json"):
        p = page_dir / candidate
        if p.exists():
            return p
    return page_dir / "shared" / "planner_input.json"


def _sub_urls(page_dir: Path) -> Path:
    for candidate in ("phase_1_crawl/sub_urls.txt", "sub_urls.txt"):
        p = page_dir / candidate
        if p.exists():
            return p
    return page_dir / "sub_urls.txt"


def _shots_dir(page_dir: Path) -> Path:
    p1 = page_dir / "phase_1_crawl" / "screenshots"
    if p1.exists() and any(p1.glob("page_*.png")):
        return p1
    if (page_dir / "phase_1_crawl").exists() and any((page_dir / "phase_1_crawl").glob("page_*.png")):
        return page_dir / "phase_1_crawl"
    return page_dir


@router.get("/{slug_or_run_id}/manifest")
def artifacts_manifest(slug_or_run_id: str) -> dict:
    _, page_dir, manifest = page_dir_for(slug_or_run_id)

    def phase_files(pdir: Path) -> list[str]:
        if not pdir.exists():
            return []
        out = []
        for f in pdir.rglob("*"):
            if len(out) >= 500:
                break
            try:
                if f.is_file():
                    out.append(str(f.relative_to(pdir)))
            except Exception:
                continue
        return sorted(out)

    phases = {}
    for name in ("shared", "phase_1_crawl", "phase_2_ground", "phase_3_plan",
                 "phase_4_execute", "phase_5_verify", "phase_6_report"):
        d = page_dir / name
        phases[name] = {"exists": d.exists(), "files": phase_files(d)}
    return {"slug_or_run_id": slug_or_run_id, "phases": phases, "manifest": manifest}


@router.get("/{slug_or_run_id}/planner-input")
def planner_input(slug_or_run_id: str) -> dict:
    _, page_dir, _ = page_dir_for(slug_or_run_id)
    f = _planner_input(page_dir)
    if not f.exists():
        raise HTTPException(404, "planner_input.json not found.")
    return json.loads(f.read_text(encoding="utf-8"))


@router.get("/{slug_or_run_id}/sub-urls", response_class=PlainTextResponse)
def sub_urls(slug_or_run_id: str) -> str:
    _, page_dir, _ = page_dir_for(slug_or_run_id)
    f = _sub_urls(page_dir)
    return f.read_text(encoding="utf-8") if f.exists() else ""


@router.get("/{slug_or_run_id}/screenshot")
def primary_screenshot(slug_or_run_id: str):
    _, page_dir, _ = page_dir_for(slug_or_run_id)
    shots = _shots_dir(page_dir) / "page_annotated.png"
    if not shots.exists():
        shots = page_dir / "page_annotated.png"
    if not shots.exists():
        raise HTTPException(404, "Screenshot not found.")
    return FileResponse(str(shots), media_type="image/png")


@router.get("/{slug_or_run_id}/folds/{fold_num}")
def fold_screenshot(slug_or_run_id: str, fold_num: int):
    _, page_dir, _ = page_dir_for(slug_or_run_id)
    shot = _shots_dir(page_dir) / f"page_annotated_fold_{fold_num}.png"
    if not shot.exists():
        shot = page_dir / f"page_annotated_fold_{fold_num}.png"
    if not shot.exists():
        raise HTTPException(404, f"Fold {fold_num} screenshot not found.")
    return FileResponse(str(shot), media_type="image/png")


@router.get("/{slug_or_run_id}/file/{rel_path:path}")
def artifact_file(slug_or_run_id: str, rel_path: str):
    _, page_dir, _ = page_dir_for(slug_or_run_id)
    try:
        target = safe_join(page_dir, rel_path)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    if not target.exists() or not target.is_file():
        raise HTTPException(404, "Artifact not found.")
    media = "image/png" if target.suffix == ".png" else "application/json"
    return FileResponse(str(target), media_type=media)
