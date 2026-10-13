"""Evidence gate — classify BEFORE any judge. No regex shortcuts; evidence-required.

Deterministic classification only. A candidate is eligible for judging only
when it carries reproducible evidence (a replayed assertion failure). Harness /
guardrail / test-plan failures are dismissed here and never become 'product'
defects.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

# failure_class values that can never be a product defect
NON_PRODUCT = frozenset({"harness", "guardrail_block", "test-plan", "blocked_bot", "env_error", "timeout"})


@dataclass
class GateDecision:
    eligible: bool          # proceed to replay + judge?
    verdict: str            # "DISMISSED" | "NEEDS_REPLAY"
    failure_class: str
    reasoning: str


def evaluate_gate(candidate: dict[str, Any]) -> GateDecision:
    """Classify one candidate finding. Deterministic, no LLM."""
    fclass = (candidate.get("failure_class") or "unclassified").strip()
    err = (candidate.get("error_message") or "").strip()
    if fclass in NON_PRODUCT:
        return GateDecision(False, "DISMISSED", fclass,
                            f"Dismissed at gate: '{fclass}' is not a product defect. {err}".strip())
    if not err:
        return GateDecision(False, "DISMISSED", fclass,
                            "Dismissed at gate: no error evidence on the candidate.")
    return GateDecision(True, "NEEDS_REPLAY", fclass,
                        f"Eligible for replay + judge ({fclass}). {err}".strip())
