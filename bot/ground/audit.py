"""Pure grounding audit — schema + refs + box + files. No LLM, no browser."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from bot.ids import safe_join

_REQUIRED_KEYS = frozenset({
    "schema_version", "objective", "page", "user_state", "constraints",
    "headings", "components", "navigation_summary", "artifacts",
})
_VALID_ROLES = frozenset({
    "textbox", "searchbox", "button", "link", "checkbox", "radio",
    "combobox", "listbox", "switch", "slider", "spinbutton", "tab", "option",
})
_REF_RE = re.compile(r"^@e\d+$")

_ISSUE_BUCKETS = ("validator", "box", "refs", "folds", "files")


@dataclass
class GroundResult:
    total: int
    ok_count: int
    issues: list[str] = field(default_factory=list)
    by_type: dict[str, int] = field(default_factory=lambda: {b: 0 for b in _ISSUE_BUCKETS})
    rows: list[list[str]] = field(default_factory=list)


def _viewport(planner: dict[str, Any]) -> tuple[int, int]:
    vp = (planner.get("page", {}) or {}).get("viewport", {}) or {}
    try:
        return int(vp.get("width", 1280)), int(vp.get("height", 900))
    except (TypeError, ValueError):
        return 1280, 900


def _parse_box(box: Any) -> tuple[int, int, int, int] | None:
    if isinstance(box, (list, tuple)) and len(box) == 4:
        try:
            return int(box[0]), int(box[1]), int(box[2]), int(box[3])
        except (TypeError, ValueError):
            return None
    if isinstance(box, str) and box.count(",") == 3:
        try:
            x1, y1, x2, y2 = (int(p) for p in box.split(","))
            return x1, y1, x2, y2
        except ValueError:
            return None
    return None


def validate_contract(planner: dict[str, Any]) -> list[str]:
    """Layer A — schema compliance. Returns a list of error strings."""
    errors: list[str] = []
    if planner.get("schema_version") != "planner-input-v1":
        errors.append(f"schema_version != planner-input-v1 (got {planner.get('schema_version')!r})")
    missing = _REQUIRED_KEYS - set(planner.keys())
    if missing:
        errors.append(f"missing required keys: {sorted(missing)}")
    if not planner.get("objective"):
        errors.append("objective is empty")
    page = planner.get("page", {})
    if not page.get("url"):
        errors.append("page.url is missing")
    components = planner.get("components")
    if not components or not isinstance(components, list):
        errors.append("components is empty or not a list")
    return errors


def check_grounding(planner: dict[str, Any], page_dir: Path | None = None) -> GroundResult:
    """Layer B — geometric + on-disk fold/file binding audit."""
    width, height = _viewport(planner)
    components = planner.get("components", []) or []
    result = GroundResult(total=len(components), ok_count=0)

    fold_files: dict[int, Path] = {}
    has_dir = page_dir is not None and Path(page_dir).exists()
    if has_dir:
        shots = safe_join(Path(page_dir), "phase_1_crawl", "screenshots")
        if shots.is_dir():
            for p in shots.glob("page_annotated_fold_*.png"):
                m = re.search(r"fold_(\d+)", p.name)
                if m:
                    fold_files[int(m.group(1))] = p

    seen_refs: set[str] = set()
    for c in components:
        ref = c.get("ref", "")
        role = c.get("role", "")
        comp_issues: list[str] = []

        if not _REF_RE.match(ref or ""):
            comp_issues.append(f"bad ref format '{ref}'")
            result.by_type["refs"] += 1
        elif ref in seen_refs:
            comp_issues.append(f"duplicate ref '{ref}'")
            result.by_type["refs"] += 1
        seen_refs.add(ref)

        if role not in _VALID_ROLES:
            comp_issues.append(f"invalid role '{role}'")
            result.by_type["validator"] += 1

        box = _parse_box(c.get("box"))
        if box is None:
            comp_issues.append(f"unparseable box '{c.get('box')}'")
            result.by_type["box"] += 1
        else:
            x1, y1, x2, y2 = box
            if x2 <= x1 or y2 <= y1:
                comp_issues.append(f"degenerate box {box}")
                result.by_type["box"] += 1
            elif x1 < -width or y1 < -height or x2 > 2 * width or y2 > 2 * height:
                comp_issues.append(f"box {box} outside viewport {width}x{height}")
                result.by_type["box"] += 1

        folds = c.get("visible_in_folds") or []
        if not isinstance(folds, list):
            folds = []
        if fold_files:
            missing = [f for f in folds if f not in fold_files]
            if missing:
                comp_issues.append(f"folds {missing} not on disk")
                result.by_type["folds"] += 1

        if not comp_issues:
            result.ok_count += 1
        else:
            result.issues.extend(f"{ref}: {msg}" for msg in comp_issues)
        result.rows.append([ref, role, c.get("name") or "(unnamed)", str(c.get("box", "")),
                            str(folds), "OK" if not comp_issues else "; ".join(comp_issues)])
    return result
