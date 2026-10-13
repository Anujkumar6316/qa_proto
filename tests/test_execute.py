"""Execute runner tests — pass/fail/blocked/budget, session close, findings."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from bot.execute import run_execution  # noqa: E402


def _plan(steps: list[dict], **tc_extra) -> dict:
    tc = {"id": "TC_001", "title": "t", "category": "functional", "severity": "P2_major",
          "safety_gated": False, "steps": steps}
    tc.update(tc_extra)
    return {"plan_version": "qa-plan-v1", "target_url": "https://example.com/login",
            "test_suite": "s", "thought_analysis": "t", "test_cases": [tc]}


def test_passing_case() -> None:
    plan = _plan([
        {"action": "fill", "target_ref": "@e1", "value": "user@example.com"},
        {"action": "click", "target_ref": "@e2"},
        {"action": "assert_visible", "target_ref": "@e2"},
    ])
    ex = run_execution(plan)
    assert ex["execution_version"] == "qa-execution-v1"
    assert ex["summary"]["passed_cases"] == 1
    assert ex["summary"]["candidate_findings_count"] == 0


def test_failing_assert_emits_candidate() -> None:
    plan = _plan([
        {"action": "click", "target_ref": "@e2"},
        {"action": "assert_url_contains", "target_ref": None, "value": "/dashboard"},
    ])
    ex = run_execution(plan)
    assert ex["summary"]["failed_cases"] == 1
    assert ex["summary"]["candidate_findings_count"] == 1
    finding = ex["candidate_findings"][0]
    assert finding["failure_class"] == "unclassified"


def test_locator_not_found_is_harness_not_product() -> None:
    plan = _plan([
        {"action": "click", "target_ref": "@e99"},
        {"action": "assert_visible", "target_ref": "@e99"},
    ])
    ex = run_execution(plan)
    assert ex["candidate_findings"][0]["failure_class"] == "harness"


def test_safety_gated_blocked_without_sandbox() -> None:
    plan = _plan([
        {"action": "click", "target_ref": "@e2"},
        {"action": "assert_visible", "target_ref": "@e2"},
    ], safety_gated=True)
    ex = run_execution(plan)
    assert ex["summary"]["blocked_cases"] == 1
    assert ex["summary"]["candidate_findings_count"] == 0
    # sandbox unlocks it
    ex2 = run_execution(plan, sandbox=True)
    assert ex2["summary"]["passed_cases"] == 1


def test_step_budget_exceeded_is_test_plan() -> None:
    plan = _plan([{"action": "click", "target_ref": "@e2"}] * 9 + [
        {"action": "assert_visible", "target_ref": "@e2"}])
    ex = run_execution(plan, max_steps=6)
    assert ex["candidate_findings"][0]["failure_class"] == "test-plan"


def test_session_closed_per_case() -> None:
    from bot.execute.fake_driver import FakeExecDriver
    created: list[FakeExecDriver] = []
    orig_init = FakeExecDriver.__init__

    def tracking_init(self, **kw):
        orig_init(self, **kw)
        created.append(self)

    FakeExecDriver.__init__ = tracking_init
    try:
        plan = _plan([
            {"action": "click", "target_ref": "@e2"},
            {"action": "assert_visible", "target_ref": "@e2"},
        ])
        run_execution(plan)
    finally:
        FakeExecDriver.__init__ = orig_init
    assert len(created) == 1 and created[0]._closed == 1
