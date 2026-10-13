"""Plan service tests — LLM-only providers + fail-closed grounding gate."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from bot.plan import PlanProviderError, run_plan  # noqa: E402
from bot.plan.providers import OpenAICompatPlanProvider, _extract_json  # noqa: E402


def _write_input(page_dir: Path, components: list[dict]) -> None:
    shared = page_dir / "shared"
    shared.mkdir(parents=True, exist_ok=True)
    (shared / "planner_input.json").write_text(json.dumps({
        "schema_version": "planner-input-v1", "objective": "o",
        "page": {"url": "https://example.com", "title": "T"},
        "user_state": {}, "constraints": {}, "headings": [],
        "components": components, "navigation_summary": {}, "artifacts": {},
    }), encoding="utf-8")


class StubChat:
    """Fake langchain chat object — no network. Returns a canned grounded plan."""

    def __init__(self, payload: str) -> None:
        self._payload = payload

    def invoke(self, messages):
        class R:
            content = self._payload
        return R()


PLAN_JSON = json.dumps({
    "plan_version": "qa-plan-v1", "target_url": "https://example.com",
    "test_suite": "stub", "thought_analysis": "t",
    "test_cases": [{
        "id": "TC_001", "title": "Fill and submit", "category": "functional",
        "severity": "P3_minor", "hypothesis": "h", "safety_gated": False,
        "expected_outcome": "o",
        "steps": [
            {"action": "fill", "target_ref": "@e1", "value": "user@example.com"},
            {"action": "click", "target_ref": "@e2"},
            {"action": "assert_visible", "target_ref": "@e2"},
        ],
    }],
})


def test_llm_provider_plan_passes_gate(tmp_path: Path, monkeypatch) -> None:
    _write_input(tmp_path, [
        {"ref": "@e1", "role": "textbox", "name": "Email", "box": [0, 0, 100, 20]},
        {"ref": "@e2", "role": "button", "name": "Go", "box": [0, 30, 100, 50]},
    ])
    provider = OpenAICompatPlanProvider(model="test-model", api_key="sk-test")
    monkeypatch.setattr(provider, "_chat", lambda: StubChat(f"```json\n{PLAN_JSON}\n```"))
    plan, path = run_plan(tmp_path, provider, run_id="abcdef01")
    assert plan["plan_version"] == "qa-plan-v1"
    assert plan["test_cases"][0]["id"] == "TC_001"
    assert path.name == "qa_plan.json"
    assert "run_id" in json.loads(path.read_text())


def test_missing_api_key_is_hard_fail(tmp_path: Path, monkeypatch) -> None:
    """No mock fallback: without a key, planning raises a clear provider error."""
    from bot.settings import get_settings
    monkeypatch.setattr(get_settings(), "LLM_API_KEY", "", raising=False)
    _write_input(tmp_path, [
        {"ref": "@e1", "role": "textbox", "name": "Email", "box": [0, 0, 100, 20]},
        {"ref": "@e2", "role": "button", "name": "Go", "box": [0, 30, 100, 50]},
    ])
    with pytest.raises(PlanProviderError, match="API key"):
        run_plan(tmp_path)


def test_extract_json_handles_fenced_and_plain() -> None:
    assert _extract_json(PLAN_JSON)["plan_version"] == "qa-plan-v1"
    assert _extract_json(f"here you go:\n```json\n{PLAN_JSON}\n```hope it helps")["test_cases"]
    with pytest.raises(PlanProviderError):
        _extract_json("no json at all")


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
        run_plan(tmp_path, OpenAICompatPlanProvider(model="m", api_key="sk-test"))


def test_missing_input_raises(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        run_plan(tmp_path)
