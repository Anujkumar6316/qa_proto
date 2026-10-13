"""Phase 4 Execute router."""

from __future__ import annotations

import json

from fastapi import APIRouter, HTTPException

from bot.interfaces.api.session import session_slot
from bot.interfaces.api.resolve import artifacts_root, load_plan, page_dir_for, rel
from bot.interfaces.api.schemas import ExecuteRequest

router = APIRouter(prefix="/execute", tags=["Phase 4 — Execute"])


def _run(slug_or_run_id: str, req: ExecuteRequest) -> dict:
    from bot.execute import run_execution
    _, page_dir, _ = page_dir_for(slug_or_run_id)
    plan = load_plan(page_dir)
    with session_slot():  # bounded browser-session concurrency
        execution = run_execution(plan, backend=req.backend)
    # persist for later GET
    out_dir = page_dir / "phase_4_execute"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "qa_execution.json").write_text(json.dumps(execution, indent=2), encoding="utf-8")
    return execution


@router.post("")
def execute(req: ExecuteRequest) -> dict:
    return _run(req.identifier, req)


@router.get("/{slug_or_run_id}")
def get_execution(slug_or_run_id: str) -> dict:
    _, page_dir, _ = page_dir_for(slug_or_run_id)
    path = page_dir / "phase_4_execute" / "qa_execution.json"
    if not path.exists():
        raise HTTPException(409, "No execution yet — run POST /execute first.")
    return json.loads(path.read_text(encoding="utf-8"))
