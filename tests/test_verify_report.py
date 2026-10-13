"""Verify + report tests — gate/replay/judge isolation, dedupe, repro parsing."""

from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from bot.report import dedupe_verified_findings, run_report  # noqa: E402
from bot.report.repro import build_repro_spec, step_to_ts  # noqa: E402
from bot.verify import evaluate_gate, run_verification  # noqa: E402


def _exec_with(findings: list[dict]) -> dict:
    return {"execution_version": "qa-execution-v1", "target_url": "https://example.com",
            "run_id": "r", "slug": "s", "candidate_findings": findings}


_FAILING_STEPS = [
    {"action": "click", "target_ref": "@e2"},
    {"action": "assert_url_contains", "target_ref": None, "value": "/dashboard"},
]


def _plan(steps: list[dict]) -> dict:
    return {"plan_version": "qa-plan-v1", "target_url": "https://example.com",
            "test_cases": [{"id": "TC_001", "steps": steps}]}


def test_gate_dismisses_non_product() -> None:
    d = evaluate_gate({"failure_class": "harness", "error_message": "boom"})
    assert not d.eligible and d.verdict == "DISMISSED"
    d2 = evaluate_gate({"failure_class": "unclassified", "error_message": ""})
    assert not d2.eligible


def test_gate_eligible_needs_replay() -> None:
    d = evaluate_gate({"failure_class": "unclassified", "error_message": "assert failed"})
    assert d.eligible and d.verdict == "NEEDS_REPLAY"


def test_verify_reproduces_and_confirms() -> None:
    ex = _exec_with([{"id": "F1", "test_case_id": "TC_001", "step_index": 1,
                      "severity": "P1_critical", "title": "No redirect", "failure_class": "unclassified",
                      "error_message": "expected /dashboard"}])
    v = run_verification(ex, _plan(_FAILING_STEPS))
    assert v["summary"]["replayed_count"] == 1
    assert v["summary"]["verified_count"] == 1
    assert v["verified_findings"][0]["verdict"] == "VERIFIED"


def test_verify_judge_error_isolated() -> None:
    def bad_judge(c, tc, reproduced):
        raise RuntimeError("llm down")

    ex = _exec_with([{"id": "F1", "test_case_id": "TC_001", "step_index": 1, "severity": "P2_major",
                      "title": "x", "failure_class": "unclassified", "error_message": "e"}])
    v = run_verification(ex, _plan(_FAILING_STEPS), judge=bad_judge)
    assert v["summary"]["dismissed_count"] == 1  # run survives the judge crash


def test_verify_dismisses_harness_candidate() -> None:
    ex = _exec_with([{"id": "F1", "test_case_id": "TC_001", "step_index": 0, "severity": "P2_major",
                      "title": "x", "failure_class": "harness", "error_message": "locator_not_found"}])
    v = run_verification(ex, _plan(_FAILING_STEPS))
    assert v["summary"]["verified_count"] == 0 and v["summary"]["dismissed_count"] == 1


def test_dedupe_highest_confidence_wins() -> None:
    base = {"title": "No redirect", "target_ref": "@e2", "step_index": 1, "failure_class": "product"}
    a = {**base, "id": "A", "confidence": 0.7}
    b = {**base, "id": "B", "confidence": 0.95}
    unique, merged = dedupe_verified_findings([a, b])
    assert len(unique) == 1 and unique[0]["id"] == "B"
    assert merged[0]["merged_id"] == "A" and merged[0]["into_id"] == "B"


def test_repro_spec_parses_url_matcher() -> None:
    tc = _plan(_FAILING_STEPS)["test_cases"][0]
    finding = {"id": "F1", "title": "No redirect", "target_ref": "@e2"}
    spec = build_repro_spec(finding, tc, start_url="https://example.com")
    assert "toHaveURL(" in spec
    m = re.search(r"toHaveURL\((/.*/)\);", spec)
    assert m, "URL matcher must be a RegExp literal, not a bare string"
    re.compile(m.group(1))  # must compile


def test_step_to_ts_navigate_and_assert_text() -> None:
    assert "page.goto(" in step_to_ts({"action": "navigate", "value": "https://x.com"})
    assert "toContainText(" in step_to_ts({"action": "assert_text", "value": "Hi"}, {"target_ref": None})


def test_run_report_end_to_end() -> None:
    ex = _exec_with([{"id": "F1", "test_case_id": "TC_001", "step_index": 1, "severity": "P0_blocker",
                      "title": "No redirect", "category": "functional", "failure_class": "unclassified",
                      "error_message": "e"}])
    v = run_verification(ex, _plan(_FAILING_STEPS))
    report = run_report(v, _plan(_FAILING_STEPS))
    assert report["report_version"] == "qa-report-v1"
    assert report["summary"]["total_verified"] == 1
    assert report["summary"]["severity_matrix"]["P0_blocker"] == 1
    assert report["repro_files"] and report["_specs"][report["repro_files"][0]]
