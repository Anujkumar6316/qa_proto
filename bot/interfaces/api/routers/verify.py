"""Phase 5 Verify router."""

from __future__ import annotations

import json

from fastapi import APIRouter, HTTPException

from bot.interfaces.api.session import session_slot
from bot.interfaces.api.resolve import load_plan, page_dir_for
from bot.interfaces.api.schemas import IdentifierRequest

router = APIRouter(prefix="/verify", tags=["Phase 5 — Verify"])


def _run(slug_or_run_id: str) -> dict:
    from bot.execute import run_execution
    from bot.verify import run_verification
    _, page_dir, _ = page_dir_for(slug_or_run_id)
    plan = load_plan(page_dir)
    with session_slot():  # bounded browser-session concurrency
        execution = run_execution(plan, backend="fake")
        verification = run_verification(execution, plan, page_dir=page_dir)
    out_dir = page_dir / "phase_5_verify"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "qa_verification.json").write_text(json.dumps(verification, indent=2), encoding="utf-8")
    return verification


@router.post("")
def verify(request: IdentifierRequest) -> dict:
    return _run(request.identifier)


@router.get("/{slug_or_run_id}")
def get_verification(slug_or_run_id: str) -> dict:
    _, page_dir, _ = page_dir_for(slug_or_run_id)
    path = page_dir / "phase_5_verify" / "qa_verification.json"
    if not path.exists():
        raise HTTPException(409, "No verification yet — run POST /verify first.")
    return json.loads(path.read_text(encoding="utf-8"))
