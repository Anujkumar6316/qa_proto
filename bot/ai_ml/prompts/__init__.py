"""Prompt library — one prompt per named file. Loaded by loader.py, never inlined."""

from __future__ import annotations

from bot.ai_ml.prompts.loader import SCENARIOS, STRATEGIES, load_prompt, load_scenario, load_strategy

__all__ = ["SCENARIOS", "STRATEGIES", "load_prompt", "load_scenario", "load_strategy"]
