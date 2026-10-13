"""Phase 2 Ground router."""

from __future__ import annotations

from fastapi import APIRouter

from bot.interfaces.api.resolve import artifacts_root, page_dir_for, rel
from bot.interfaces.api.schemas import IdentifierRequest

router = APIRouter(prefix="/ground", tags=["Phase 2 — Ground"])


@router.post("")
def ground(request: IdentifierRequest) -> dict:
    from bot.ground import run_ground
    _, page_dir, _ = page_dir_for(request.identifier)
    result, audit = run_ground(page_dir)
    return {"slug_or_run_id": request.identifier, "total": result.total,
            "ok_count": result.ok_count, "by_type": result.by_type,
            "issues": result.issues, "audit": rel(artifacts_root(), audit)}
