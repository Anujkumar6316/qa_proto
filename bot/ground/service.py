"""Ground service — load planner_input, run audit, persist artifacts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from bot.events import emit
from bot.ground.audit import GroundResult, check_grounding, validate_contract
from bot.ids import new_run_id, safe_join


def load_planner_input(page_dir: Path) -> dict[str, Any]:
    for candidate in ("shared/planner_input.json", "phase_1_crawl/planner_input.json", "planner_input.json"):
        p = safe_join(page_dir, *candidate.split("/"))
        if p.exists():
            return json.loads(p.read_text(encoding="utf-8"))
    raise FileNotFoundError(f"planner_input.json not found under {page_dir}")


def run_ground(page_dir: Path, *, run_id: str | None = None) -> tuple[GroundResult, Path]:
    run_id = run_id or new_run_id()
    planner = load_planner_input(page_dir)
    errors = validate_contract(planner)
    ground = check_grounding(planner, page_dir=page_dir)
    for e in errors:
        ground.issues.append(f"contract: {e}")
        ground.by_type["validator"] += 1

    out_dir = safe_join(page_dir, "phase_2_ground")
    out_dir.mkdir(parents=True, exist_ok=True)
    audit_path = safe_join(out_dir, "grounding_audit.json")
    audit_path.write_text(json.dumps({
        "run_id": run_id,
        "total": ground.total,
        "ok_count": ground.ok_count,
        "issues": ground.issues,
        "by_type": ground.by_type,
    }, indent=2), encoding="utf-8")
    emit(page_dir, "ground", "ground.completed", {
        "run_id": run_id, "total": ground.total, "ok_count": ground.ok_count,
        "issues_by_type": ground.by_type,
    }, artifacts={"audit": str(audit_path)})
    return ground, audit_path
