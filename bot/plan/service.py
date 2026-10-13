"""Plan service — provider emits candidate, grounding gate enforces. Fail-closed.

No mock provider: a plan is produced only by a real LLM provider (langchain-openai,
OpenAI-compatible). Missing configuration or a failed call is a hard error.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Protocol

from bot.events import emit
from bot.ids import new_run_id, relative_ref, safe_join
from bot.plan.grounding import validate_plan_grounding
from bot.plan.providers import build_plan_provider


class PlanProvider(Protocol):
    def generate(self, planner_input: dict[str, Any]) -> dict[str, Any]:
        ...


def collect_registry(planner_input: dict[str, Any]) -> tuple[set[str], dict[str, str]]:
    refs, fps = set(), {}
    for c in planner_input.get("components", []):
        ref = c.get("ref")
        if ref:
            refs.add(ref)
            if c.get("fingerprint"):
                fps[ref] = c["fingerprint"]
    return refs, fps


def run_plan(
    page_dir: Path,
    provider: PlanProvider | None = None,
    *,
    run_id: str | None = None,
    strategy: str = "comprehensive",
    model: str | None = None,
    base_url: str | None = None,
    api_key: str | None = None,
) -> tuple[dict[str, Any], Path]:
    """Generate a plan with the configured LLM provider, enforce the grounding gate,
    persist qa_plan.json. Fail-closed: no provider argument => real OpenAI-compatible
    provider from .env / overrides; there is no mock fallback."""
    run_id = run_id or new_run_id()
    provider = provider or build_plan_provider(strategy, model=model,
                                               base_url=base_url, api_key=api_key)

    from bot.ground.service import load_planner_input
    planner_input = load_planner_input(page_dir)
    refs, fingerprints = collect_registry(planner_input)
    if not refs:
        raise ValueError("Grounding fail-closed: no @eN components in planner_input")

    plan = provider.generate(planner_input)
    errors = validate_plan_grounding(plan, refs, fingerprints or None)
    if errors:
        raise ValueError(f"Grounding gate rejected plan: {errors[:5]}")

    out_dir = safe_join(page_dir, "phase_3_plan")
    out_dir.mkdir(parents=True, exist_ok=True)
    plan_path = safe_join(out_dir, "qa_plan.json")
    plan["run_id"] = run_id
    plan_path.write_text(json.dumps(plan, indent=2), encoding="utf-8")
    emit(page_dir, "plan", "plan.generated", {
        "run_id": run_id, "cases": len(plan.get("test_cases", [])),
        "provider": type(provider).__name__,
    }, artifacts={"plan": relative_ref(page_dir, plan_path)})
    return plan, plan_path
