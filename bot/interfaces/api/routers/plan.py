"""Phase 3 Plan router."""

from __future__ import annotations

import json

from fastapi import APIRouter, HTTPException

from bot.interfaces.api.resolve import artifacts_root, load_plan, page_dir_for, rel
from bot.interfaces.api.schemas import PlanRequest, PlanResponse

router = APIRouter(prefix="/plan", tags=["Phase 3 — Plan"])


def _to_response(slug: str, plan: dict, plan_ref: str) -> PlanResponse:
    return PlanResponse(
        plan_version=plan.get("plan_version", "qa-plan-v1"), slug=slug,
        run_id=plan.get("run_id", ""), target_url=plan.get("target_url", ""),
        test_suite=plan.get("test_suite", ""), thought_analysis=plan.get("thought_analysis", ""),
        test_cases_count=len(plan.get("test_cases", [])),
        test_cases=plan.get("test_cases", []), plan_ref=plan_ref)


@router.post("", response_model=PlanResponse)
def create_plan(request: PlanRequest) -> PlanResponse:
    """Generate a grounded plan with the configured LLM provider.

    Planning is LLM-only (langchain-openai, OpenAI-compatible): per-request
    `model`/`base_url`/`api_key` overrides win, otherwise `.env` defaults are used.
    A missing or failed provider configuration is a hard 502 — there is no mock.
    """
    from bot.plan import PlanProviderError, run_plan
    _, page_dir, _ = page_dir_for(request.identifier)
    if request.provider not in (None, "", "openai-compatible"):
        raise HTTPException(422, f"Unsupported provider '{request.provider}'. "
                                 "Only 'openai-compatible' (LLM-only) is supported.")
    try:
        plan, path = run_plan(page_dir, strategy=request.strategy,
                              model=request.model, base_url=request.base_url,
                              api_key=request.api_key)
    except PlanProviderError as exc:
        raise HTTPException(502, f"Planner provider failed: {exc}") from exc
    except (ValueError, FileNotFoundError) as exc:
        raise HTTPException(422, str(exc)) from exc
    return _to_response(page_dir.name, plan, rel(artifacts_root(), path))


@router.get("/{slug_or_run_id}", response_model=PlanResponse)
def get_plan(slug_or_run_id: str) -> PlanResponse:
    _, page_dir, _ = page_dir_for(slug_or_run_id)
    plan = load_plan(page_dir)
    path = page_dir / "phase_3_plan" / "qa_plan.json"
    return _to_response(page_dir.name, plan, rel(artifacts_root(), path))
