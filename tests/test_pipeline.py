"""End-to-end pipeline: crawl -> ground -> plan -> execute -> verify -> report."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from bot.crawl import run_crawl  # noqa: E402
from bot.execute import run_execution  # noqa: E402
from bot.ground import run_ground  # noqa: E402
from bot.plan import run_plan  # noqa: E402


class _StubPlanProvider:
    """Deterministic in-test provider (the production pipeline is LLM-only; tests
    inject a provider directly instead of relying on a mock fallback)."""

    name = "stub"

    def generate(self, planner_input):
        refs = [c["ref"] for c in planner_input.get("components", []) if c.get("ref")]
        return {
            "plan_version": "qa-plan-v1",
            "target_url": planner_input.get("page", {}).get("url", ""),
            "test_suite": "stub",
            "thought_analysis": "stub",
            "test_cases": [{
                "id": "TC_001", "title": "Page has an interactive component",
                "category": "functional", "severity": "P2_minor",
                "hypothesis": "component responds", "safety_gated": False,
                "expected_outcome": "no crash",
                "steps": [{"action": "assert_present", "target_ref": refs[0],
                           "value": None, "note": "stub"}],
            }],
        }

from bot.report import run_report  # noqa: E402
from bot.verify import run_verification  # noqa: E402


def test_full_six_phase_chain(tmp_path: Path) -> None:
    manifest = run_crawl("https://example.com/login", tmp_path, backend="fake")
    page_dir = tmp_path / "example_com__login" / "pages" / "example_com__login"
    run_id = manifest["run_id"]

    ground, _ = run_ground(page_dir, run_id=run_id)
    assert ground.ok_count == 2

    plan, _ = run_plan(page_dir, _StubPlanProvider(), run_id=run_id)

    execution = run_execution(plan, backend="fake", target_url=plan["target_url"], run_id=run_id)
    assert execution["summary"]["total_cases"] == 1

    verification = run_verification(execution, plan, run_id=run_id, page_dir=page_dir)
    assert verification["summary"]["total_candidates"] == execution["summary"]["candidate_findings_count"]

    report = run_report(verification, plan, run_id=run_id, page_dir=page_dir)
    assert report["report_version"] == "qa-report-v1"

    # Every phase emitted an event, in order
    events = [json.loads(l) for l in (page_dir / "events.jsonl").read_text().splitlines()]
    assert [e["phase"] for e in events] == ["crawl", "ground", "plan", "verify", "report"]


def test_chain_with_a_real_defect(tmp_path: Path) -> None:
    """A plan whose terminal assert fails must surface as a VERIFIED defect + repro."""
    manifest = run_crawl("https://example.com/login", tmp_path, backend="fake")
    page_dir = tmp_path / "example_com__login" / "pages" / "example_com__login"

    # Hand-build a plan that will fail at execution (click navigates nowhere,
    # assert expects /dashboard). Uses real refs so it passes the grounding gate.
    from bot.plan.grounding import validate_plan_grounding
    failing_plan = {
        "plan_version": "qa-plan-v1", "target_url": "https://example.com/login",
        "test_suite": "s", "thought_analysis": "t",
        "test_cases": [{
            "id": "TC_001", "title": "Login redirects", "category": "functional",
            "severity": "P0_blocker", "hypothesis": "h", "safety_gated": False,
            "expected_outcome": "redirect to /dashboard",
            "steps": [
                {"action": "click", "target_ref": "@e2", "description": "login"},
                {"action": "assert_url_contains", "target_ref": None, "value": "/dashboard"},
            ],
        }],
    }
    assert validate_plan_grounding(failing_plan, {"@e1", "@e2"}) == []

    execution = run_execution(failing_plan, backend="fake")
    assert execution["summary"]["candidate_findings_count"] == 1

    verification = run_verification(execution, failing_plan)
    assert verification["summary"]["verified_count"] == 1

    report = run_report(verification, failing_plan)
    assert report["summary"]["total_verified"] == 1
    assert report["summary"]["repro_count"] == 1
    assert report["defects"][0]["severity"] == "P0_blocker"
    assert "toHaveURL(" in report["_specs"][report["repro_files"][0]]
