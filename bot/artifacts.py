"""Shared artifact-layout helpers — one source of truth for phase directory names.

Both the CLI (`bot.interfaces.cli`) and the API (`bot.interfaces.api.resolve`)
resolve a crawl manifest to its page directory, and every service writes its
phase output under `<page_dir>/<phase_N_name>/`. Those conventions used to be
duplicated in several modules; keep them here so they can never drift.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

# Canonical phase directory names (also used by the artifacts router listing).
SHARED_DIR = "shared"
PHASE_DIRS: dict[str, str] = {
    "crawl": "phase_1_crawl",
    "ground": "phase_2_ground",
    "plan": "phase_3_plan",
    "execute": "phase_4_execute",
    "verify": "phase_5_verify",
    "report": "phase_6_report",
}

# Where each phase persists its primary JSON artifact, relative to page_dir.
PLANNER_INPUT_REF = f"{SHARED_DIR}/planner_input.json"
PLAN_ARTIFACT_REF = f"{PHASE_DIRS['plan']}/qa_plan.json"
EXECUTION_ARTIFACT_REF = f"{PHASE_DIRS['execute']}/qa_execution.json"
VERIFICATION_ARTIFACT_REF = f"{PHASE_DIRS['verify']}/qa_verification.json"
REPORT_ARTIFACT_REF = f"{PHASE_DIRS['report']}/qa_report.json"

# planner_input.json lookup order (crawl writes it to shared/, legacy layouts vary).
PLANNER_INPUT_CANDIDATES = (
    PLANNER_INPUT_REF,
    f"{PHASE_DIRS['crawl']}/planner_input.json",
    "planner_input.json",
)


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: Any) -> Path:
    """Write pretty JSON, creating parent directories as needed."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return path


def load_manifest(manifest_path: Path) -> dict[str, Any]:
    """Load a site_manifest.json written by Phase 1."""
    return read_json(manifest_path)


def page_dir_from_manifest(manifest: dict[str, Any], root: Path) -> Path:
    """Derive the page directory from a manifest's first page `shared_dir` ref.

    The manifest stores a root-relative POSIX ref like
    ``<slug>/pages/<slug>/shared``; the page dir is its parent. Never returns
    a path inside ``shared/`` itself.
    """
    ref = manifest["pages"][0]["artifacts"]["shared_dir"]
    page_dir = (root / ref).resolve()
    if page_dir.name == SHARED_DIR:
        page_dir = page_dir.parent
    return page_dir


def plan_path(page_dir: Path) -> Path:
    return page_dir / PLAN_ARTIFACT_REF


def phase_dir(page_dir: Path, phase: str) -> Path:
    """`<page_dir>/<phase_N_name>` for a key of PHASE_DIRS (created on demand)."""
    return page_dir / PHASE_DIRS[phase]
