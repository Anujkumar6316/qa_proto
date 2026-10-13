"""Prompt library tests — every file loads, matches its frozen source, no drift."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pytest  # noqa: E402

from bot.ai_ml.prompts import SCENARIOS, STRATEGIES, load_prompt, load_scenario, load_strategy  # noqa: E402

# Frozen sources in the legacy repo (byte-identical parity check).
LEGACY = ROOT.parent
LEGACY_MAP = {
    "planner/strategies/comprehensive.md": "core/pipeline/plan/strategy_prompts/comprehensive.md",
    "planner/strategies/journey.md": "core/pipeline/plan/strategy_prompts/journey.md",
    "planner/strategies/negative_edge.md": "core/pipeline/plan/strategy_prompts/negative_edge.md",
    "planner/strategies/positive_flow.md": "core/pipeline/plan/strategy_prompts/positive_flow.md",
    "planner/strategies/security_injection.md": "core/pipeline/plan/strategy_prompts/security_injection.md",
    "planner/strategies/strict_adversarial.md": "core/pipeline/plan/strategy_prompts/strict_adversarial.md",
}


@pytest.mark.parametrize("name", STRATEGIES)
def test_strategy_loads(name: str) -> None:
    text = load_strategy(name)
    assert text.strip()
    assert "Target QA Strategy" in text


@pytest.mark.parametrize("name", SCENARIOS)
def test_scenario_loads(name: str) -> None:
    assert load_scenario(name).strip()


def test_system_and_templates_load() -> None:
    assert "QA Automation Planner" in load_prompt("planner/system.md")
    assert "{strategy_guide}" in load_prompt("planner/user_template.md")
    assert "Adversarial QA Verifier Judge" in load_prompt("judge/system.md")
    assert "Principal QA Automation Architect" in load_prompt("teacher/system.md")


def test_loader_rejects_traversal_and_missing() -> None:
    with pytest.raises(ValueError):
        load_prompt("../../../etc/passwd")
    with pytest.raises(FileNotFoundError):
        load_prompt("planner/does_not_exist.md")


@pytest.mark.parametrize("local,legacy", list(LEGACY_MAP.items()))
def test_strategy_matches_legacy_byte_identical(local: str, legacy: str) -> None:
    src = LEGACY / legacy
    if not src.exists():
        pytest.skip(f"legacy source not present: {legacy}")
    assert load_prompt(local) == src.read_text(encoding="utf-8")


def test_no_scaffold_placeholder_remains() -> None:
    # The old skeleton placeholders used these exact phrases — must be gone.
    scaffold_markers = ("replace this placeholder", "todo_existing_contract", "scaffold only")
    for rel in ("planner/system.md", "judge/system.md", "teacher/system.md"):
        low = load_prompt(rel).lower()
        assert not any(m in low for m in scaffold_markers), rel
