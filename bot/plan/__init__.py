"""Plan layer — grounding gate (pure) + plan service (fail-closed, LLM-only providers)."""

from __future__ import annotations

from bot.plan.grounding import validate_plan_grounding
from bot.plan.providers import (
    OpenAICompatPlanProvider,
    PlanProviderError,
    build_plan_provider,
)
from bot.plan.service import PlanProvider, run_plan

__all__ = [
    "OpenAICompatPlanProvider", "PlanProvider", "PlanProviderError",
    "build_plan_provider", "run_plan", "validate_plan_grounding",
]
