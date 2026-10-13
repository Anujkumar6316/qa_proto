"""Plan service — provider emits candidate, grounding gate enforces. Fail-closed."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Protocol

from bot.events import emit
from bot.ids import new_run_id, relative_ref, safe_join
from bot.plan.grounding import validate_plan_grounding


class PlanProvider(Protocol):
    def generate(self, planner_input: dict[str, Any]) -> dict[str, Any]:
        ...


class MockPlanProvider:
    """Deterministic offline provider — one grounded happy-path case per component pair."""

    def generate(self, planner_input: dict[str, Any]) -> dict[str, Any]:
        comps = [c["ref"] for c in planner_input.get("components", []) if c.get("ref")]
        if len(comps) < 2:
            raise ValueError("Cannot mock-plan fewer than 2 components")
        target, control = comps[0], comps[1]
        return {
            "plan_version": "qa-plan-v1",
            "target_url": planner_input.get("page", {}).get("url", ""),
            "test_suite": "mock-smoke",
            "thought_analysis": "Deterministic mock plan for offline testing.",
            "test_cases": [{
                "id": "TC_001", "title": "Mock interaction smoke", "category": "functional",
                "severity": "P3_minor", "hypothesis": "Element responds to interaction.",
                "steps": [
                    {"action": "fill", "target_ref": target, "value": "user@example.com"},
                    {"action": "click", "target_ref": control},
                    {"action": "assert_visible", "target_ref": control},
                ],
                "safety_gated": False,
                "expected_outcome": "Interaction completes without error.",
            }],
        }


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
) -> tuple[dict[str, Any], Path]:
    """Generate a plan, enforce grounding gate (single retry), persist qa_plan.json."""
    run_id = run_id or new_run_id()
    provider = provider or MockPlanProvider()

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
