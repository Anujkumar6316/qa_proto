"""Ground audit tests — fail-closed, no browser, no LLM."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from bot.ground import check_grounding, run_ground, validate_contract  # noqa: E402

_VALID: dict = {
    "schema_version": "planner-input-v1",
    "objective": "test login",
    "page": {"url": "https://example.com/login", "title": "Login", "viewport": {"width": 1280, "height": 900}},
    "user_state": {"authenticated": False, "role": "guest"},
    "constraints": {"max_test_cases": 8},
    "headings": [],
    "components": [
        {"ref": "@e1", "role": "textbox", "name": "Email", "box": [10, 20, 200, 40], "visible_in_folds": [1]},
        {"ref": "@e2", "role": "button", "name": "Login", "box": [10, 60, 200, 90], "visible_in_folds": [1]},
    ],
    "navigation_summary": {"internal_links": []},
    "artifacts": {},
}


def test_valid_contract_passes() -> None:
    assert validate_contract(_VALID) == []


def test_missing_keys_and_version_rejected() -> None:
    errors = validate_contract({"schema_version": "planner-input-v2", "components": []})
    assert any("schema_version" in e for e in errors)
    assert any("missing required keys" in e for e in errors)
    assert any("components is empty" in e for e in errors)
    assert any("objective" in e for e in errors)


def test_grounding_clean_page() -> None:
    g = check_grounding(_VALID)
    assert g.total == 2 and g.ok_count == 2
    assert g.issues == []


def test_grounding_bad_ref_role_box_duplicate() -> None:
    bad = {"components": [
        {"ref": "e9", "role": "textbox", "box": [0, 0, 10, 10]},          # bad ref
        {"ref": "@e1", "role": "wizard", "box": [5, 5, 50, 20]},           # bad role
        {"ref": "@e2", "role": "button", "box": "garbage"},                # bad box
        {"ref": "@e3", "role": "link", "box": [10, 20, 10, 20]},            # degenerate (x2<=x1)
        {"ref": "@e3", "role": "link", "box": [10, 20, 10, 20]},            # duplicate
    ], "page": {"viewport": {"width": 1280, "height": 900}}}
    g = check_grounding(bad)
    assert g.ok_count == 0
    assert g.by_type["refs"] >= 2 and g.by_type["validator"] >= 1 and g.by_type["box"] >= 2


def test_fold_binding_checked_when_dir_present(tmp_path: Path) -> None:
    shots = tmp_path / "phase_1_crawl" / "screenshots"
    shots.mkdir(parents=True)
    (shots / "page_annotated_fold_1.png").write_bytes(b"fake")
    planner = {"components": [
        {"ref": "@e1", "role": "button", "box": [0, 0, 10, 10], "visible_in_folds": [1, 2]},
    ], "page": {"viewport": {"width": 1280, "height": 900}}}
    g = check_grounding(planner, page_dir=tmp_path)
    assert g.by_type["folds"] == 1
    assert any("folds [2] not on disk" in i for i in g.issues)


def test_run_ground_persists_and_emits(tmp_path: Path) -> None:
    shared = tmp_path / "shared"
    shared.mkdir(parents=True)
    (shared / "planner_input.json").write_text(json.dumps(_VALID), encoding="utf-8")
    ground, audit_path = run_ground(tmp_path, run_id="abcdef01")
    assert ground.ok_count == 2
    assert audit_path.name == "grounding_audit.json"
    events = [json.loads(l) for l in (tmp_path / "events.jsonl").read_text().splitlines()]
    assert events[0]["event"] == "ground.completed"
    assert events[0]["attrs"]["run_id"] == "abcdef01"


def test_missing_planner_input_raises(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        run_ground(tmp_path)
