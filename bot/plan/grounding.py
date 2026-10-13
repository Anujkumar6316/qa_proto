"""Grounding gate — reject hallucinated @eN refs and malformed plans. Pure."""

from __future__ import annotations

from typing import Any, Final

from bot.execute.driver import ASSERT_ACTIONS as _ASSERT_ACTIONS  # noqa: F401 (shared source)

# Actions that may omit target_ref (page-level or global):
#   assert_text (dynamic feedback via value), assert_url_contains (page-level),
#   press_key (global), navigate (URL in value).
ACTION_STEPS: Final[frozenset[str]] = frozenset({
    "click", "fill", "hover", "press_key", "scroll_into_view", "navigate",
    "select", "check", "uncheck", "scroll",
})
ASSERT_ACTIONS: Final[frozenset[str]] = _ASSERT_ACTIONS
REF_REQUIRED_ACTIONS: Final[frozenset[str]] = (ACTION_STEPS - {"press_key", "navigate", "scroll"}) | {
    "assert_attr", "assert_visible", "assert_hidden",
}
VALID_PLAN_VERSIONS: Final[frozenset[str]] = frozenset({"qa-plan-v1", "qa-plan-v2"})
PLACEHOLDER_FILLS: Final[frozenset[str]] = frozenset({"test", "foo", "bar", "asdf", "placeholder"})


def validate_plan_grounding(
    qa_plan: dict[str, Any],
    valid_refs: set[str],
    ref_fingerprints: dict[str, str] | None = None,
    page_registries: dict[str, set[str]] | None = None,
    page_fingerprints: dict[str, dict[str, str]] | None = None,
) -> list[str]:
    """Return grounding errors (empty = valid). No LLM, no I/O.

    Enforces: plan_version enum, non-empty test_cases, valid ids, >=2 steps,
    terminal assertion, refs in the known set, selector-fingerprint match
    (catches invented selectors), concrete fill values, assert_attr attribute.
    """
    errors: list[str] = []
    if not isinstance(qa_plan, dict):
        return ["QA Plan must be a JSON object"]

    if qa_plan.get("plan_version") not in VALID_PLAN_VERSIONS:
        errors.append(f"Invalid plan_version: expected {sorted(VALID_PLAN_VERSIONS)}, got '{qa_plan.get('plan_version')}'")

    all_known = set(valid_refs)
    for p_refs in (page_registries or {}).values():
        all_known.update(p_refs)

    test_cases = qa_plan.get("test_cases")
    if not test_cases or not isinstance(test_cases, list):
        errors.append("Plan must contain a non-empty list of 'test_cases'")
        return errors

    seen_ids: set[str] = set()
    for idx, tc in enumerate(test_cases):
        tid = tc.get("id", f"<tc#{idx}>")
        if not isinstance(tc, dict):
            errors.append(f"{tid}: not an object")
            continue
        if tc.get("id") in seen_ids:
            errors.append(f"{tid}: duplicate test case id")
        seen_ids.add(tc.get("id"))

        steps = tc.get("steps", [])
        if not isinstance(steps, list) or len(steps) < 2:
            errors.append(f"{tid}: needs >= 2 steps (got {len(steps) if isinstance(steps, list) else 'n/a'})")
            continue
        last_action = steps[-1].get("action") if isinstance(steps[-1], dict) else None
        if last_action not in ASSERT_ACTIONS:
            errors.append(f"{tid}: last step must be an assertion (got '{last_action}')")

        for si, step in enumerate(steps):
            if not isinstance(step, dict):
                errors.append(f"{tid} step {si}: not an object")
                continue
            action = step.get("action")
            page_ctx = step.get("page_context")
            step_refs = set(valid_refs)
            if page_ctx and page_registries and page_ctx in page_registries:
                step_refs = page_registries[page_ctx]
            elif page_registries and not page_ctx:
                step_refs = all_known

            ref = step.get("target_ref")
            if not ref and action in REF_REQUIRED_ACTIONS:
                errors.append(f"{tid} step {si}: '{action}' requires non-null target_ref")
            elif ref and ref not in step_refs:
                ctx_hint = f"page '{page_ctx}'" if page_ctx else "page"
                errors.append(f"{tid} step {si}: unknown ref '{ref}' (not in {ctx_hint} components)")

            if action == "assert_text" and not ref and not str(step.get("value", "") or "").strip():
                errors.append(f"{tid} step {si}: assert_text with null target_ref requires non-empty value")
            if action == "fill" and str(step.get("value", "")).strip().lower() in PLACEHOLDER_FILLS:
                errors.append(f"{tid} step {si}: placeholder fill '{step.get('value')}' not allowed")
            if action == "assert_attr" and not step.get("attribute"):
                errors.append(f"{tid} step {si}: assert_attr requires 'attribute'")

            selector = step.get("target_selector")
            if selector and ref:
                fp_map = (page_fingerprints or {}).get(page_ctx, {}) if page_ctx else (ref_fingerprints or {})
                expected = fp_map.get(ref)
                if expected and selector != expected:
                    errors.append(
                        f"{tid} step {si}: target_selector mismatch for '{ref}' "
                        f"(plan '{selector}' != registry '{expected}')"
                    )
    return errors
