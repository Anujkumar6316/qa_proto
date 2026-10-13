"""Execute runner — bounded loop over qa-plan steps -> qa-execution-v1.

One driver session per test case (fresh context). Enforces guardrails + step
budget, captures per-step evidence, emits candidate findings. The runner NEVER
claims 'product' — it classifies harness/test-plan/guardrail/server-error and
leaves product verdicts to Phase 5.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any

from bot.execute.assertions import (
    eval_attr, eval_hidden, eval_text_candidates, eval_url_contains, eval_visible,
)
from bot.execute.guardrails import evaluate_action, validate_step_budget

ASSERT_ACTIONS = frozenset({
    "assert_url_contains", "assert_text", "assert_attr", "assert_visible", "assert_hidden",
})


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _driver_factory(backend: str):
    if backend == "fake":
        from bot.execute.fake_driver import FakeExecDriver
        return FakeExecDriver
    raise ValueError(f"Unknown execute backend '{backend}'")


def _finding(tc: dict[str, Any], si: int, title: str, fclass: str, err: str) -> dict[str, Any]:
    return {"id": f"{tc.get('id')}_S{si}", "test_case_id": tc.get("id"), "step_index": si,
            "category": tc.get("category", "functional"), "severity": tc.get("severity", "P2_major"),
            "title": title, "target_ref": tc.get("target_ref"),
            "failure_class": fclass, "error_message": err or ""}


async def _evaluate_assert(driver: Any, action: str, ref: str | None,
                           value: str | None, attribute: str | None) -> tuple[bool, str, str | None]:
    if action == "assert_url_contains":
        return eval_url_contains(await driver.current_url(), value or "")
    if action == "assert_text":
        return eval_text_candidates([await driver.page_text()], value or "")
    if action == "assert_attr":
        r = await driver.resolve(ref) if ref else {"ok": False}
        return eval_attr(r.get("attr"), value or "", attribute or "")
    if action == "assert_visible":
        r = await driver.resolve(ref) if ref else {"ok": False, "visible": False}
        return eval_visible(bool(r.get("visible")), ref)
    if action == "assert_hidden":
        r = await driver.resolve(ref) if ref else {"ok": False, "visible": False}
        return eval_hidden(bool(r.get("visible")), ref)
    return False, "", f"unknown assert action '{action}'"

async def _run_case(driver: Any, tc: dict[str, Any], *, target_url: str,
                    allowed_domains: set[str], sandbox: bool, max_steps: int) -> dict[str, Any]:
    base = {"id": tc.get("id"), "title": tc.get("title"), "category": tc.get("category"),
            "severity": tc.get("severity"), "target_ref": tc.get("target_ref")}
    if tc.get("safety_gated") and not sandbox:
        return {**base, "status": "blocked_safety_gated", "steps": [], "findings": []}

    steps = tc.get("steps", [])
    ok_budget, budget_err = validate_step_budget(steps, max_steps)
    if not ok_budget:
        return {**base, "status": "errored", "steps": [],
                "findings": [_finding(tc, -1, "Step budget exceeded", "test-plan", budget_err or "")]}

    opened = await driver.goto(target_url)
    if not opened.get("ok"):
        return {**base, "status": "errored", "steps": [],
                "findings": [_finding(tc, 0, "Navigation failed", "harness", opened.get("error", ""))]}

    steps_out: list[dict[str, Any]] = []
    findings: list[dict[str, Any]] = []
    status = "passed"

    for si, step in enumerate(steps):
        action, ref = step.get("action"), step.get("target_ref")
        value, attribute = step.get("value"), step.get("attribute")

        if action in ASSERT_ACTIONS:
            passed, actual, err = await _evaluate_assert(driver, action, ref, value, attribute)
            steps_out.append({"step_index": si, "action": action,
                              "status": "passed" if passed else "failed",
                              "duration_ms": 0, "actual": actual, "error": err})
            if not passed:
                status = "failed"
                findings.append(_finding(tc, si, f"Assertion failed: {action}", "unclassified", err or ""))
            continue

        resolved = None
        if ref:
            resolved = await driver.resolve(ref)
            if not resolved.get("ok"):
                findings.append(_finding(tc, si, f"Locator not found: {ref}", "harness", f"locator_not_found {ref}"))
                steps_out.append({"step_index": si, "action": action, "status": "errored",
                                  "duration_ms": 0, "error": f"locator not found for {ref}"})
                return {**base, "status": "errored", "steps": steps_out, "findings": findings}

        allowed, reason = evaluate_action(action, target_name=step.get("description", ""), value=value,
                                          allowed_domains=allowed_domains, sandbox_mode=sandbox)
        if not allowed:
            findings.append(_finding(tc, si, "Guardrail blocked action", "guardrail_block", reason or ""))
            steps_out.append({"step_index": si, "action": action, "status": "blocked",
                              "duration_ms": 0, "error": reason})
            return {**base, "status": "errored", "steps": steps_out, "findings": findings}

        result = await driver.act(action, resolved, value=value, attribute=attribute)
        if not result.get("ok"):
            findings.append(_finding(tc, si, f"Action failed: {action}", "harness", result.get("error", "")))
            steps_out.append({"step_index": si, "action": action, "status": "errored",
                              "duration_ms": 0, "error": result.get("error", "")})
            return {**base, "status": "errored", "steps": steps_out, "findings": findings}
        steps_out.append({"step_index": si, "action": action, "status": "passed", "duration_ms": 0})

    return {**base, "status": status, "steps": steps_out, "findings": findings}


def run_execution(plan: dict[str, Any], *, backend: str = "fake", target_url: str = "",
                  allowed_domains: set[str] | None = None, sandbox: bool = False,
                  max_steps: int = 6, run_id: str | None = None) -> dict[str, Any]:
    """Execute every test case in a plan. Returns a qa-execution-v1 dict."""
    from bot.ids import new_run_id
    run_id = run_id or new_run_id()
    target_url = target_url or plan.get("target_url", "")
    driver_cls = _driver_factory(backend)
    t0 = datetime.now(timezone.utc)

    async def _run_all() -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        for tc in plan.get("test_cases", []):
            driver = driver_cls()
            try:
                out.append(await _run_case(driver, tc, target_url=target_url,
                                           allowed_domains=allowed_domains or set(),
                                           sandbox=sandbox, max_steps=max_steps))
            finally:
                await driver.close()
        return out

    results = asyncio.run(_run_all())
    all_findings = [f for r in results for f in r.get("findings", [])]
    total_steps = sum(len(r.get("steps", [])) for r in results)
    passed_steps = sum(1 for r in results for s in r.get("steps", []) if s.get("status") == "passed")
    return {
        "execution_version": "qa-execution-v1", "target_url": target_url, "run_id": run_id,
        "slug": plan.get("slug", ""), "started_at": t0.isoformat(), "completed_at": _now(),
        "duration_ms": int((datetime.now(timezone.utc) - t0).total_seconds() * 1000),
        "sandbox_mode": sandbox, "backend": backend,
        "summary": {
            "total_cases": len(results),
            "passed_cases": sum(1 for r in results if r["status"] == "passed"),
            "failed_cases": sum(1 for r in results if r["status"] == "failed"),
            "blocked_cases": sum(1 for r in results if r["status"] == "blocked_safety_gated"),
            "total_steps": total_steps, "passed_steps": passed_steps,
            "failed_steps": total_steps - passed_steps,
            "candidate_findings_count": len(all_findings),
        },
        "test_case_results": [{k: v for k, v in r.items() if k != "findings"} for r in results],
        "candidate_findings": all_findings,
    }

