"""Assertion evaluators — deterministic, pure. Ported from legacy, isolated."""

from __future__ import annotations


def _norm_ws(text: str | None) -> str:
    return " ".join((text or "").split())


def eval_url_contains(current_url: str, expected: str) -> tuple[bool, str, str | None]:
    actual = current_url or ""
    exp = (expected or "").strip()
    if exp in actual:
        return True, actual, None
    return False, actual, f"Expected URL to contain '{exp}', but got '{actual}'"


def eval_text_candidates(candidates: list[str | None], expected: str) -> tuple[bool, str, str | None]:
    exp = _norm_ws(expected).lower()
    first = ""
    for cand in candidates:
        if cand is None:
            continue
        cleaned = _norm_ws(str(cand))
        if not first and cleaned:
            first = cleaned
        if exp and exp in cleaned.lower():
            return True, cleaned, None
    return False, first, f"Expected text containing '{expected}', but found '{first}'"


def eval_attr(actual_value: str | None, expected: str, attribute: str) -> tuple[bool, str, str | None]:
    actual = (actual_value or "").strip()
    exp = (expected or "").strip()
    if exp and (exp == actual or exp in actual):
        return True, actual, None
    return False, actual, f"Expected attribute '{attribute}' to contain '{exp}', but got '{actual}'"


def eval_visible(is_visible: bool, target_ref: str | None = None) -> tuple[bool, str, str | None]:
    desc = f"element '{target_ref}'" if target_ref else "element"
    actual = "visible" if is_visible else "hidden/absent"
    if is_visible:
        return True, actual, None
    return False, actual, f"Expected {desc} to be visible, but it was not visible"


def eval_hidden(is_visible: bool, target_ref: str | None = None) -> tuple[bool, str, str | None]:
    desc = f"element '{target_ref}'" if target_ref else "element"
    actual = "visible" if is_visible else "hidden/absent"
    if not is_visible:
        return True, actual, None
    return False, actual, f"Expected {desc} to be hidden/absent, but it is visible"
