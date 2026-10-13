"""Playwright repro synthesis — emit runnable .spec.ts from a verified finding.

URL matchers are always emitted as strings or escaped RegExp (never a bare
'/path' literal that fails to parse), per legacy Task 3.
"""

from __future__ import annotations

import json
import re
from typing import Any

_SAFE_TITLE = re.compile(r"[^A-Za-z0-9_]+")


def _url_matcher(expected: str) -> str:
    """Return a runnable expect() URL matcher for a substring."""
    raw = (expected or "").strip()
    if not raw:
        return '""'
    esc = re.escape(raw).replace("/", r"\/")
    return f'/{esc}/'


def _selector(finding: dict[str, Any]) -> str:
    sel = finding.get("target_selector")
    if sel:
        return json.dumps(sel)
    return json.dumps(f"[data-ref='{finding.get('target_ref', '')}']")


def step_to_ts(step: dict[str, Any], finding: dict[str, Any] | None = None) -> str:
    action = step.get("action")
    merged = {**(finding or {}), **(step or {})}
    sel = _selector(merged)
    if action == "navigate":
        return f"  await page.goto({json.dumps(step.get('value', ''))});"
    if action == "click":
        return f"  await page.locator({sel}).click();"
    if action == "fill":
        return f"  await page.locator({sel}).fill({json.dumps(step.get('value', ''))});"
    if action == "hover":
        return f"  await page.locator({sel}).hover();"
    if action == "press_key":
        return f"  await page.keyboard.press({json.dumps(step.get('value', 'Enter'))});"
    if action == "assert_url_contains":
        return f"  await expect(page).toHaveURL({_url_matcher(step.get('value', ''))});"
    if action == "assert_text":
        ref = step.get("target_ref")
        target = f"page.locator({sel})" if ref else "page"
        return f"  await expect({target}).toContainText({json.dumps(step.get('value', ''))});"
    if action == "assert_visible":
        return f"  await expect(page.locator({sel})).toBeVisible();"
    if action == "assert_hidden":
        return f"  await expect(page.locator({sel})).toBeHidden();"
    if action == "assert_attr":
        return f"  await expect(page.locator({sel})).toHaveAttribute({json.dumps(step.get('attribute', ''))}, /{re.escape(str(step.get('value','')))}/);"
    return f"  // unsupported action: {action}"


def build_repro_spec(finding: dict[str, Any], test_case: dict[str, Any], *,
                     start_url: str = "") -> str:
    tc_id = _SAFE_TITLE.sub("_", str(finding.get("id", "finding"))) or "finding"
    lines = [
        "import { test, expect } from '@playwright/test';",
        "",
        f"test('repro {tc_id}: {str(finding.get('title', ''))[:80]}', async ({{ page }}) => {{",
        f"  await page.goto({json.dumps(start_url or finding.get('target_url', ''))});",
    ]
    for step in test_case.get("steps", []):
        lines.append(step_to_ts(step, finding))
    lines.append("});")
    lines.append("")
    return "\n".join(lines)
