"""Phase 3 test-case card rendering (pure functions — never raise, never touch disk).

Ported from the root project's qa_studio_cards.py, self-contained for v0.2.
`_TC_CSS` is injected once per gr.HTML component by the caller.
"""

from __future__ import annotations

_SEVERITY_STYLES: dict[str, dict[str, str]] = {
    "P0_blocker": {"color": "#dc2626", "bg": "#fef2f2", "label": "P0 · Blocker"},
    "P1_critical": {"color": "#ea580c", "bg": "#fff7ed", "label": "P1 · Critical"},
    "P2_major": {"color": "#ca8a04", "bg": "#fefce8", "label": "P2 · Major"},
    "P3_minor": {"color": "#16a34a", "bg": "#f0fdf4", "label": "P3 · Minor"},
}
_CATEGORY_ICONS: dict[str, str] = {
    "functional": "✓", "positive": "✓", "negative_edge": "✗", "negative": "✗",
    "security": "\U0001f512", "security_injection": "\U0001f512", "navigation": "→",
    "dynamic_ui": "⚡", "boundary": "⊞", "validation": "⊘", "state_transition": "⇄",
    "interaction": "⇄", "error_handling": "⚠", "regression": "↺", "destructive_action": "☠",
    "journey": "🧭",
}
_ACTION_ICONS: dict[str, str] = {
    "click": "\U0001f446", "fill": "✏", "hover": "\U0001f441", "press_key": "⌨",
    "navigate": "🧭", "assert_visible": "✓", "assert_url_contains": "✓",
    "assert_text": "✓", "assert_not_visible": "✗", "assert_hidden": "✗",
    "assert_attr": "✓", "wait": "⏱", "select": "☑", "check": "☑", "uncheck": "☐",
    "scroll": "↕", "screenshot": "\U0001f4f7",
}


def _severity_style(severity: str) -> dict[str, str]:
    return _SEVERITY_STYLES.get(severity, _SEVERITY_STYLES["P2_major"])


def _category_icon(category: str) -> str:
    return _CATEGORY_ICONS.get(category, "•")


def _action_icon(action: str) -> str:
    return _ACTION_ICONS.get(action, "•")


def _html_escape(text: object) -> str:
    return (str(text).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


def render_summary_bar(plan_data: dict) -> str:
    if not isinstance(plan_data, dict):
        return ""
    test_cases = plan_data.get("test_cases", [])
    if not isinstance(test_cases, list):
        return ""
    total = len(test_cases)
    severity_counts: dict[str, int] = {}
    category_counts: dict[str, int] = {}
    for tc in test_cases:
        if not isinstance(tc, dict):
            continue
        sev = tc.get("severity", "unknown")
        cat = tc.get("category", "unknown")
        severity_counts[sev] = severity_counts.get(sev, 0) + 1
        category_counts[cat] = category_counts.get(cat, 0) + 1
    parts = [f'<span class="tc-stat tc-stat-total">{total} cases</span>']
    for sev, count in sorted(severity_counts.items()):
        style = _severity_style(sev)
        parts.append(f'<span class="tc-stat" style="color:{style["color"]};background:{style["bg"]}">'
                     f'{style["label"]}: {count}</span>')
    for cat, count in sorted(category_counts.items()):
        parts.append(f'<span class="tc-stat">{_category_icon(cat)} {_html_escape(cat)}: {count}</span>')
    return '<div class="tc-summary-bar">' + "".join(parts) + "</div>"

def render_test_cases_html(plan_data: dict) -> str:
    if not isinstance(plan_data, dict):
        return '<div class="tc-cards-empty">No plan data.</div>'
    test_cases = plan_data.get("test_cases", [])
    if not isinstance(test_cases, list) or not test_cases:
        return '<div class="tc-cards-empty">No test cases in this plan.</div>'
    cards = [render_test_case_card(tc) for tc in test_cases if isinstance(tc, dict)]
    return '<div class="tc-cards-container">' + "".join(cards) + "</div>"


def render_test_case_card(tc: dict) -> str:
    style = _severity_style(tc.get("severity", ""))
    tc_id = _html_escape(tc.get("id", "?"))
    title = _html_escape(tc.get("title", ""))
    category = _html_escape(tc.get("category", ""))
    cat_icon = _category_icon(tc.get("category", ""))
    target_ref = _html_escape(tc.get("target_ref") or "")
    hypothesis = _html_escape(tc.get("hypothesis", ""))
    expected = _html_escape(tc.get("expected_outcome", ""))
    safety_gated = bool(tc.get("safety_gated"))

    step_items = []
    for step in tc.get("steps", []) or []:
        if not isinstance(step, dict):
            continue
        icon = _action_icon(step.get("action", ""))
        action = _html_escape(step.get("action", ""))
        ref = step.get("target_ref")
        ref_html = f'<span class="tc-step-ref">{_html_escape(ref)}</span>' if ref else ""
        val = step.get("value")
        val_html = f'<span class="tc-step-val">{_html_escape(val)}</span>' if val else ""
        desc = _html_escape(step.get("description", ""))
        step_items.append(
            f'<li class="tc-step"><span class="tc-step-icon">{icon}</span>'
            f'<span class="tc-step-action">{action}</span>{ref_html}{val_html}'
            f'<span class="tc-step-desc">{desc}</span></li>')
    steps_html = '<ol class="tc-steps">' + "".join(step_items) + "</ol>" if step_items else ""

    precond_html = ""
    preconditions = tc.get("preconditions")
    if isinstance(preconditions, list) and preconditions:
        items = "".join(f'<li class="tc-precond">{_html_escape(p)}</li>' for p in preconditions)
        precond_html = f'<div class="tc-preconds"><span class="tc-label">Preconditions:</span><ul>{items}</ul></div>'

    safety_html = ('<span class="tc-safety tc-safety-gated">⚠ Safety Gated</span>'
                   if safety_gated else '<span class="tc-safety tc-safety-ok">✓ Not Gated</span>')
    target_html = f'<span class="tc-target">{target_ref}</span>' if target_ref else ""
    hyp_html = f'<div class="tc-hypothesis">{hypothesis}</div>' if hypothesis else ""
    exp_html = (f'<div class="tc-expected"><span class="tc-label">Expected:</span> {expected}</div>'
                if expected else "")

    return f"""<div class="tc-card" style="border-left-color:{style['color']}">
  <div class="tc-card-header"><span class="tc-card-id">{tc_id}</span>
    <span class="tc-card-title">{title}</span>
    <span class="tc-badge" style="color:{style['color']};background:{style['bg']}">{style['label']}</span></div>
  <div class="tc-card-meta"><span class="tc-cat">{cat_icon} {category}</span>{target_html}{safety_html}</div>
  {hyp_html}{steps_html}{exp_html}{precond_html}</div>"""


_TC_CSS = """<style>
.tc-summary-bar { display: flex; flex-wrap: wrap; gap: 8px; padding: 12px 0; }
.tc-stat { padding: 4px 10px; border-radius: 12px; font-size: 13px; font-weight: 500; }
.tc-stat-total { background: #e0e7ff; color: #3730a3; }
.tc-cards-container { display: flex; flex-direction: column; gap: 12px; max-height: 600px; overflow-y: auto; padding: 4px; }
.tc-card { background: #fff; border: 1px solid #e5e7eb; border-left: 4px solid #ccc; border-radius: 8px; padding: 14px 16px; box-shadow: 0 1px 3px rgba(0,0,0,0.06); }
.tc-card-header { display: flex; align-items: center; gap: 10px; margin-bottom: 6px; flex-wrap: wrap; }
.tc-card-id { font-family: monospace; font-size: 13px; font-weight: 700; color: #6b7280; }
.tc-card-title { font-size: 15px; font-weight: 600; color: #111827; flex: 1; }
.tc-badge { padding: 2px 8px; border-radius: 10px; font-size: 11px; font-weight: 700; }
.tc-card-meta { display: flex; gap: 12px; font-size: 12px; color: #6b7280; margin-bottom: 8px; flex-wrap: wrap; }
.tc-target { font-family: monospace; background: #f3f4f6; padding: 1px 6px; border-radius: 4px; }
.tc-safety-ok { color: #16a34a; } .tc-safety-gated { color: #dc2626; }
.tc-hypothesis { font-size: 13px; color: #4b5563; margin-bottom: 8px; font-style: italic; }
.tc-steps { margin: 0 0 8px 0; padding-left: 0; list-style: none; }
.tc-step { display: flex; align-items: center; gap: 6px; padding: 3px 0; font-size: 13px; }
.tc-step-icon { width: 20px; text-align: center; }
.tc-step-action { font-family: monospace; font-weight: 600; color: #374151; }
.tc-step-ref { font-family: monospace; background: #f3f4f6; padding: 0 4px; border-radius: 3px; font-size: 12px; }
.tc-step-val { color: #7c3aed; font-size: 12px; } .tc-step-desc { color: #6b7280; font-size: 12px; }
.tc-expected { font-size: 13px; color: #374151; margin-bottom: 4px; }
.tc-label { font-weight: 600; color: #6b7280; }
.tc-preconds { font-size: 12px; color: #6b7280; }
.tc-preconds ul { margin: 2px 0 0 0; padding-left: 18px; }
.tc-cards-empty { padding: 24px; text-align: center; color: #9ca3af; font-size: 14px; }
</style>"""

