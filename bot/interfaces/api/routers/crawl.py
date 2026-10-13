"""Phase 1 Crawl router."""

from __future__ import annotations

import json
from typing import Union

from fastapi import APIRouter, HTTPException, Query, Response, status

from bot.interfaces.api.session import session_slot
from bot.interfaces.api.resolve import artifacts_root, find_crawl_dir, rel
from bot.interfaces.api.schemas import CrawlListItem, CrawlRequest, CrawlResponse

router = APIRouter(prefix="/crawl", tags=["Phase 1 — Crawl"])


@router.post("", response_model=CrawlResponse, status_code=status.HTTP_201_CREATED)
def start_crawl(request: CrawlRequest) -> CrawlResponse:
    from bot.crawl import run_crawl
    try:
        with session_slot():  # bounded browser-session concurrency
            manifest = run_crawl(request.url, artifacts_root(), backend=request.backend,
                                 scope=request.scope, objective=request.objective or None,
                                 allow_private=request.allow_private)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    except Exception as exc:
        raise HTTPException(500, f"Crawl failed: {exc}") from exc
    page = manifest["pages"][0]
    return CrawlResponse(run_id=manifest["run_id"], base_url=manifest["base_url"],
                         slug=page["slug"], components_count=page.get("components_count", 0),
                         manifest=manifest)


@router.get("", response_model=list[CrawlListItem])
def list_crawls(limit: int = Query(20, ge=1, le=100)) -> list[CrawlListItem]:
    root = artifacts_root()
    items: list[CrawlListItem] = []
    if root.exists():
        for d in sorted(root.iterdir(), key=lambda p: p.name, reverse=True):
            mani = d / "site_manifest.json"
            if d.is_dir() and mani.exists():
                try:
                    m = json.loads(mani.read_text(encoding="utf-8"))
                    items.append(CrawlListItem(slug=d.name, run_id=m.get("run_id"),
                                               base_url=m.get("base_url"),
                                               components_count=m["pages"][0].get("components_count", 0)))
                except Exception:
                    items.append(CrawlListItem(slug=d.name))
            if len(items) >= limit:
                break
    return items


@router.get("/{slug_or_run_id}", response_model=CrawlResponse)
def get_crawl(slug_or_run_id: str) -> CrawlResponse:
    crawl_dir = find_crawl_dir(slug_or_run_id)
    manifest = json.loads((crawl_dir / "site_manifest.json").read_text(encoding="utf-8"))
    page = manifest["pages"][0]
    return CrawlResponse(run_id=manifest["run_id"], base_url=manifest["base_url"],
                         slug=page["slug"], components_count=page.get("components_count", 0),
                         manifest=manifest)
