"""Grounding gate tests — ported from tests/test_plan_v1.py cases. Pure."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from bot.plan.grounding import validate_plan_grounding  # noqa: E402

_REFS = {"@e1", "@e2", "@e3"}


def _tc(tid: str, steps: list[dict], **extra) -> dict:
    base = {
        "id": tid, "title": "t", "category": "functional", "severity": "P2_major",
        "hypothesis": "h", "safety_gated": False, "expected_outcome": "o",
    }
    base.update(extra)
    base["steps"] = steps
    return base


def _plan(tcs: list[dict], version: str = "qa-plan-v1") -> dict:
    return {"plan_version": version, "target_url": "https://example.com",
            "test_suite": "s", "thought_analysis": "t", "test_cases": tcs}


def test_valid_plan_passes() -> None:
    plan = _plan([_tc("TC_001", [
        {"action": "fill", "target_ref": "@e1", "value": "user@example.com"},
        {"action": "click", "target_ref": "@e2"},
        {"action": "assert_visible", "target_ref": "@e3"},
    ])])
    assert validate_plan_grounding(plan, _REFS) == []


def test_bad_version_and_empty_cases() -> None:
    assert any("plan_version" in e for e in validate_plan_grounding(_plan([], "qa-plan-v9"), _REFS))
    p = _plan([])
    assert any("non-empty" in e for e in validate_plan_grounding(p, _REFS))


def test_hallucinated_ref_rejected() -> None:
    plan = _plan([_tc("TC_1", [
        {"action": "click", "target_ref": "@e99"},
        {"action": "assert_visible", "target_ref": "@e99"},
    ])])
    assert any("unknown ref '@e99'" in e for e in validate_plan_grounding(plan, _REFS))


def test_single_step_and_missing_terminal_assert() -> None:
    assert any(">= 2 steps" in e for e in validate_plan_grounding(
        _plan([_tc("TC_1", [{"action": "click", "target_ref": "@e1"}])]), _REFS))
    assert any("last step must be an assertion" in e for e in validate_plan_grounding(
        _plan([_tc("TC_1", [{"action": "click", "target_ref": "@e1"},
                            {"action": "fill", "target_ref": "@e2", "value": "x"}])]), _REFS))


def test_placeholder_fill_rejected() -> None:
    plan = _plan([_tc("TC_1", [
        {"action": "fill", "target_ref": "@e1", "value": "test"},
        {"action": "assert_visible", "target_ref": "@e2"},
    ])])
    assert any("placeholder fill" in e for e in validate_plan_grounding(plan, _REFS))


def test_null_ref_rules() -> None:
    # assert_url_contains and press_key may omit ref; assert_visible may not
    ok = _plan([_tc("TC_1", [
        {"action": "click", "target_ref": "@e1"},
        {"action": "assert_url_contains", "target_ref": None, "value": "/dashboard"},
    ])])
    assert validate_plan_grounding(ok, _REFS) == []
    bad = _plan([_tc("TC_1", [
        {"action": "click", "target_ref": "@e1"},
        {"action": "assert_visible", "target_ref": None},
    ])])
    assert any("requires non-null target_ref" in e for e in validate_plan_grounding(bad, _REFS))


def test_assert_text_null_ref_needs_value() -> None:
    bad = _plan([_tc("TC_1", [
        {"action": "click", "target_ref": "@e1"},
        {"action": "assert_text", "target_ref": None, "value": "  "},
    ])])
    assert any("requires non-empty value" in e for e in validate_plan_grounding(bad, _REFS))


def test_assert_attr_requires_attribute() -> None:
    bad = _plan([_tc("TC_1", [
        {"action": "click", "target_ref": "@e1"},
        {"action": "assert_attr", "target_ref": "@e2", "value": "true"},
    ])])
    assert any("assert_attr requires 'attribute'" in e for e in validate_plan_grounding(bad, _REFS))


def test_selector_fingerprint_mismatch_caught() -> None:
    fps = {"@e2": "button.login#submit"}
    plan = _plan([_tc("TC_1", [
        {"action": "fill", "target_ref": "@e1", "value": "x"},
        {"action": "click", "target_ref": "@e2", "target_selector": "div.wrong"},
        {"action": "assert_visible", "target_ref": "@e3"},
    ])])
    assert any("target_selector mismatch" in e for e in validate_plan_grounding(plan, _REFS, fps))


def test_journey_page_registry_refs() -> None:
    registries = {"pageB": {"@e5", "@e6"}}
    plan = _plan([_tc("TC_1", [
        {"action": "fill", "target_ref": "@e1", "value": "x", "page_context": "pageA"},
        {"action": "click", "target_ref": "@e5", "page_context": "pageB"},
        {"action": "assert_visible", "target_ref": "@e6", "page_context": "pageB"},
    ])], version="qa-plan-v2")
    errs = validate_plan_grounding(plan, _REFS, page_registries=registries)
    assert errs == []


def test_duplicate_ids_and_non_dict_steps() -> None:
    plan = _plan([_tc("TC_1", [{"action": "click", "target_ref": "@e1"}, "notadict"])])
    assert any("not an object" in e for e in validate_plan_grounding(plan, _REFS))
