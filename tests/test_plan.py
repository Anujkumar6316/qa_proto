"""Plan service tests — mock provider + fail-closed grounding gate."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from bot.plan import MockPlanProvider, run_plan  # noqa: E402


def _write_input(page_dir: Path, components: list[dict]) -> None:
    shared = page_dir / "shared"
    shared.mkdir(parents=True, exist_ok=True)
    (shared / "planner_input.json").write_text(json.dumps({
        "schema_version": "planner-input-v1", "objective": "o",
        "page": {"url": "https://example.com", "title": "T"},
        "user_state": {}, "constraints": {}, "headings": [],
        "components": components, "navigation_summary": {}, "artifacts": {},
    }), encoding="utf-8")


def test_mock_plan_passes_gate(tmp_path: Path) -> None:
    _write_input(tmp_path, [
        {"ref": "@e1", "role": "textbox", "name": "Email", "box": [0, 0, 100, 20]},
        {"ref": "@e2", "role": "button", "name": "Go", "box": [0, 30, 100, 50]},
    ])
    plan, path = run_plan(tmp_path, run_id="abcdef01")
    assert plan["plan_version"] == "qa-plan-v1"
    assert plan["test_cases"][0]["id"] == "TC_001"
    assert path.name == "qa_plan.json"
    assert "run_id" in json.loads(path.read_text())


def test_hallucinating_provider_rejected(tmp_path: Path) -> None:
    _write_input(tmp_path, [
        {"ref": "@e1", "role": "textbox", "name": "Email", "box": [0, 0, 100, 20]},
        {"ref": "@e2", "role": "button", "name": "Go", "box": [0, 30, 100, 50]},
    ])

    class Liar:
        def generate(self, planner_input):
            return {
                "plan_version": "qa-plan-v1", "target_url": "https://example.com",
                "test_suite": "s", "thought_analysis": "t",
                "test_cases": [{
                    "id": "TC_001", "title": "t", "category": "functional",
                    "severity": "P3_minor", "hypothesis": "h", "safety_gated": False,
                    "expected_outcome": "o",
                    "steps": [
                        {"action": "click", "target_ref": "@e99"},
                        {"action": "assert_visible", "target_ref": "@e99"},
                    ],
                }],
            }

    with pytest.raises(ValueError, match="Grounding gate rejected"):
        run_plan(tmp_path, Liar())


def test_empty_components_fails_closed(tmp_path: Path) -> None:
    _write_input(tmp_path, [])
    with pytest.raises(ValueError, match="fail-closed"):
        run_plan(tmp_path, MockPlanProvider())


def test_missing_input_raises(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        run_plan(tmp_path)
