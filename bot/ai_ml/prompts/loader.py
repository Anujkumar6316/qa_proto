"""Prompt library loader — read one prompt per named file. No prompt text in code."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

PROMPTS_DIR = Path(__file__).resolve().parent


@lru_cache(maxsize=64)
def load_prompt(relpath: str) -> str:
    """Load a prompt file by path relative to ai_ml/prompts/. Raises on miss."""
    path = (PROMPTS_DIR / relpath).resolve()
    if PROMPTS_DIR not in path.parents and path.parent != PROMPTS_DIR:
        raise ValueError(f"Prompt path escapes library: {relpath}")
    if not path.exists():
        raise FileNotFoundError(f"Prompt not found: {relpath}")
    return path.read_text(encoding="utf-8")


def load_strategy(name: str) -> str:
    """Load a planner strategy prompt (comprehensive|journey|negative_edge|...)."""
    return load_prompt(f"planner/strategies/{name}.md")


def load_scenario(name: str) -> str:
    """Load a teacher scenario prompt (smoke|negative_edge|dynamic_ui|security_validation)."""
    return load_prompt(f"teacher/scenarios/{name}.md")


STRATEGIES = ("comprehensive", "journey", "negative_edge", "positive_flow",
              "security_injection", "strict_adversarial")
SCENARIOS = ("smoke", "negative_edge", "dynamic_ui", "security_validation")
