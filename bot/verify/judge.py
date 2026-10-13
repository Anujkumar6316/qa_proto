"""Judge — one verdict per candidate. Deterministic default; pluggable via JudgeFn.

The default judge is evidence-based and offline: a candidate is VERIFIED only
when replay reproduced it AND its failure_class is product-eligible. A custom
judge (LLM) can be supplied to run_verification; a single judge failure never
loses the run (per-candidate isolation).
"""

from __future__ import annotations

from typing import Any, Callable, Protocol

from bot.verify.gate import NON_PRODUCT

JudgeFn = Callable[[dict[str, Any], dict[str, Any], bool], tuple[str, float, str]]
# (candidate, test_case, reproduced) -> (verdict, confidence, reasoning)


def default_judge(candidate: dict[str, Any], test_case: dict[str, Any],
                  reproduced: bool) -> tuple[str, float, str]:
    fclass = (candidate.get("failure_class") or "unclassified").strip()
    if fclass in NON_PRODUCT:
        return "DISMISSED", 0.9, f"failure_class '{fclass}' is not a product defect."
    if not reproduced:
        return "DISMISSED", 0.7, "Not reproduced in isolated replay — treated as flake/harness."
    return "VERIFIED", 0.85, f"Reproduced in isolated replay ({fclass}); assertion holds as a defect."
