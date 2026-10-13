"""Normalizer — snapshot -> planner-input-v1 contract. Pure, no I/O."""

from __future__ import annotations

import re
from typing import Any

_VALID_ROLES = frozenset({
    "textbox", "searchbox", "button", "link", "checkbox", "radio",
    "combobox", "listbox", "switch", "slider", "spinbutton", "tab", "option",
})
_ROLE_MAP = {
    "a": "link", "input": "textbox", "button": "button", "select": "combobox",
    "textarea": "textbox", "[role=button]": "button",
}
_REF_RE = re.compile(r"^@e(\d+)$")


def normalize_component(raw: dict[str, Any]) -> dict[str, Any]:
    role = raw.get("role", "")
    if role == "input":
        itype = (raw.get("type") or "").lower()
        role = "searchbox" if itype == "search" else "textbox"
    role = _ROLE_MAP.get(role, role)
    if role not in _VALID_ROLES:
        role = "button" if "btn" in role else "link"
    box = raw.get("box")
    box = box if isinstance(box, list) and len(box) == 4 else [0, 0, 0, 0]
    return {
        "ref": raw.get("ref", ""),
        "role": role,
        "name": raw.get("name") or "(unnamed)",
        "box": [int(box[0]), int(box[1]), int(box[2]), int(box[3])],
        "type": raw.get("type", ""),
        "fingerprint": raw.get("fingerprint", ""),
        "visible_in_folds": raw.get("visible_in_folds") or [1],
        "primary_fold": 1,
    }


def normalize_snapshot(snapshot: dict[str, Any], *, url: str, objective: str,
                       scope: str = "all") -> dict[str, Any]:
    """Build a planner-input-v1 object from a driver snapshot. Never raises."""
    raw_components = snapshot.get("components", []) or []
    components: list[dict[str, Any]] = []
    for i, rc in enumerate(raw_components):
        comp = normalize_component(rc)
        if not _REF_RE.match(comp["ref"]):
            comp["ref"] = f"@e{i + 1}"
        components.append(comp)

    return {
        "schema_version": "planner-input-v1",
        "scope": scope,
        "objective": objective,
        "page": {
            "url": url or snapshot.get("url", ""),
            "title": snapshot.get("title", ""),
            "viewport": {"width": 1280, "height": 900},
        },
        "user_state": {"authenticated": False, "role": "guest"},
        "constraints": {"max_test_cases": 8},
        "headings": [],
        "components": components,
        "navigation_summary": {"internal_links": [], "external_links": []},
        "total_folds": 1,
        "folds": [{"index": 1, "scroll_y": 0}],
        "artifacts": {"screenshot": "phase_1_crawl/screenshots/page_annotated.png"},
    }
