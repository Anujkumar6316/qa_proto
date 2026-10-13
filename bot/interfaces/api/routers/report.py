"""Phase 6 Report router."""

from __future__ import annotations

import json

from fastapi import APIRouter, HTTPException

from bot.interfaces.api.resolve import load_plan, page_dir_for
from bot.interfaces.api.schemas import ReportRequest

router = APIRouter(prefix="/report", tags=["Phase 6 — Report"])


def _run(slug_or_run_id: str, req: ReportRequest) -> dict:
    from bot.execute import run_execution
    from bot.report import run_report
    from bot.verify import run_verification
    _, page_dir, _ = page_dir_for(slug_or_run_id)
    plan = load_plan(page_dir)
    execution = run_execution(plan, backend=req.backend)
    verification = run_verification(execution, plan, page_dir=page_dir)
    rep = run_report(verification, plan, page_dir=page_dir)
    specs = rep.pop("_specs", {})
    out_dir = page_dir / "phase_6_report"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "qa_report.json").write_text(json.dumps(rep, indent=2), encoding="utf-8")
    return {**rep, "repro_specs": specs}


@router.post("")
def report(req: ReportRequest) -> dict:
    return _run(req.identifier, req)


@router.get("/{slug_or_run_id}")
def get_report(slug_or_run_id: str) -> dict:
    _, page_dir, _ = page_dir_for(slug_or_run_id)
    path = page_dir / "phase_6_report" / "qa_report.json"
    if not path.exists():
        raise HTTPException(409, "No report yet — run POST /report first.")
    return json.loads(path.read_text(encoding="utf-8"))
