"""Ground service — load planner_input, run audit, persist artifacts."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from bot.artifacts import (
    PHASE_DIRS,
    PLANNER_INPUT_CANDIDATES,
    read_json,
    write_json,
)
from bot.events import emit
from bot.ground.audit import GroundResult, check_grounding, validate_contract
from bot.ids import new_run_id, safe_join


def load_planner_input(page_dir: Path) -> dict[str, Any]:
    for candidate in PLANNER_INPUT_CANDIDATES:
        p = safe_join(page_dir, *candidate.split("/"))
        if p.exists():
            return read_json(p)
    raise FileNotFoundError(f"planner_input.json not found under {page_dir}")


def run_ground(page_dir: Path, *, run_id: str | None = None) -> tuple[GroundResult, Path]:
    run_id = run_id or new_run_id()
    planner = load_planner_input(page_dir)
    errors = validate_contract(planner)
    ground = check_grounding(planner, page_dir=page_dir)
    for e in errors:
        ground.issues.append(f"contract: {e}")
        ground.by_type["validator"] += 1

    audit_path = write_json(safe_join(page_dir, PHASE_DIRS["ground"], "grounding_audit.json"), {
        "run_id": run_id,
        "total": ground.total,
        "ok_count": ground.ok_count,
        "issues": ground.issues,
        "by_type": ground.by_type,
    })
    emit(page_dir, "ground", "ground.completed", {
        "run_id": run_id, "total": ground.total, "ok_count": ground.ok_count,
        "issues_by_type": ground.by_type,
    }, artifacts={"audit": str(audit_path)})
    return ground, audit_path
