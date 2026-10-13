"""Execute layer — bounded runner, guardrails, assertions. One session per case."""

from __future__ import annotations

from bot.execute.assertions import (
    eval_attr, eval_hidden, eval_text_candidates, eval_url_contains, eval_visible,
)
from bot.execute.driver import ExecDriver
from bot.execute.fake_driver import FakeExecDriver
from bot.execute.guardrails import evaluate_action, is_domain_allowed, validate_step_budget
from bot.execute.runner import run_execution

__all__ = [
    "ExecDriver", "FakeExecDriver", "evaluate_action", "eval_attr", "eval_hidden",
    "eval_text_candidates", "eval_url_contains", "eval_visible", "is_domain_allowed",
    "run_execution", "validate_step_budget",
]
