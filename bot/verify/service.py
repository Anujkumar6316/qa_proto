"""Verify service — gate -> replay -> judge, per-candidate isolated. qa-verification-v1."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from bot.events import emit
from bot.ids import new_run_id
from bot.verify.gate import evaluate_gate
from bot.verify.judge import JudgeFn, default_judge
from bot.verify.replayer import replay_candidate


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _merge(candidate: dict[str, Any], verdict: str, confidence: float,
           reasoning: str, reproduced: bool) -> dict[str, Any]:
    out = {**candidate, "verdict": verdict, "confidence": confidence,
           "reasoning": reasoning, "reproduced": reproduced}
    out.setdefault("evidence", {})
    return out


def run_verification(execution: dict[str, Any], plan: dict[str, Any], *,
                     target_url: str = "", backend: str = "fake",
                     judge: JudgeFn | None = None, run_id: str | None = None,
                     page_dir: Any = None) -> dict[str, Any]:
    """Adversarially verify every candidate finding. Returns qa-verification-v1."""
    run_id = run_id or new_run_id()
    judge = judge or default_judge
    target_url = target_url or execution.get("target_url", "")
    cases_by_id = {tc.get("id"): tc for tc in plan.get("test_cases", [])}
    t0 = datetime.now(timezone.utc)

    verified: list[dict[str, Any]] = []
    dismissed: list[dict[str, Any]] = []
    replayed = 0

    for candidate in execution.get("candidate_findings", []):
        tc = cases_by_id.get(candidate.get("test_case_id"), {})
        gate = evaluate_gate(candidate)
        if not gate.eligible:
            dismissed.append(_merge(candidate, "DISMISSED", 0.95, gate.reasoning, False))
            continue

        try:
            reproduced, replay_err = replay_candidate(candidate, tc, target_url=target_url, backend=backend)
            replayed += 1
        except Exception as exc:  # harness/replay failure never loses the run
            dismissed.append(_merge(candidate, "DISMISSED", 0.8, f"replay error: {exc}", False))
            continue

        try:
            verdict, confidence, reasoning = judge(candidate, tc, reproduced)
        except Exception as exc:  # per-candidate judge isolation
            verdict, confidence, reasoning = "DISMISSED", 0.5, f"judge error: {exc}"

        if reproduced and replay_err:
            reasoning = f"{reasoning} (replay: {replay_err})"
        record = _merge(candidate, verdict, confidence, reasoning, reproduced)
        (verified if verdict == "VERIFIED" else dismissed).append(record)

    total = len(execution.get("candidate_findings", []))
    result = {
        "verification_version": "qa-verification-v1", "target_url": target_url,
        "run_id": run_id, "slug": execution.get("slug", ""),
        "started_at": t0.isoformat(), "completed_at": _now(),
        "duration_ms": int((datetime.now(timezone.utc) - t0).total_seconds() * 1000),
        "summary": {
            "total_candidates": total, "verified_count": len(verified),
            "dismissed_count": len(dismissed), "replayed_count": replayed,
            "verification_rate": round(len(verified) / total, 4) if total else 0.0,
        },
        "verified_findings": verified, "dismissed_findings": dismissed,
    }
    emit(page_dir if page_dir is not None else _events_dir(plan), "verify", "verify.completed",
         {"run_id": run_id, **result["summary"]})
    return result


def _events_dir(plan: dict[str, Any]):
    from pathlib import Path
    return Path(plan.get("page_dir", ".")) if plan.get("page_dir") else Path(".")
