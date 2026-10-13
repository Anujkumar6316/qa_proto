"""Report service — dedupe verified findings + repro specs -> qa-report-v1."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from bot.events import emit
from bot.ids import new_run_id
from bot.report.dedupe import dedupe_verified_findings
from bot.report.repro import build_repro_spec

_SEVERITY_ORDER = {"P0_blocker": 0, "P1_critical": 1, "P2_major": 2, "P3_minor": 3}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def run_report(verification: dict[str, Any], plan: dict[str, Any], *,
               target_url: str = "", run_id: str | None = None,
               page_dir: Any = None) -> dict[str, Any]:
    """Build the final client report. Dedupes + synthesizes runnable repros."""
    run_id = run_id or new_run_id()
    target_url = target_url or verification.get("target_url", "")
    cases_by_id = {tc.get("id"): tc for tc in plan.get("test_cases", [])}
    verified = verification.get("verified_findings", [])

    unique, merged = dedupe_verified_findings(verified, target_url)
    unique.sort(key=lambda f: _SEVERITY_ORDER.get(f.get("severity"), 9))

    defects: list[dict[str, Any]] = []
    repro_files: list[str] = []
    for f in unique:
        tc = cases_by_id.get(f.get("test_case_id"), {})
        spec_name = f"repro_{f.get('id', 'finding')}.spec.ts"
        spec = build_repro_spec(f, tc, start_url=target_url)
        defects.append({
            "id": f.get("id"), "test_case_id": f.get("test_case_id"),
            "severity": f.get("severity"), "title": f.get("title"),
            "category": f.get("category"), "target_ref": f.get("target_ref"),
            "failure_class": f.get("failure_class", "product"),
            "error_message": f.get("error_message", ""),
            "confidence": f.get("confidence"), "reasoning": f.get("reasoning"),
            "verification_source": f.get("verification_source", "replay+judge"),
            "evidence": f.get("evidence", {}),
            "repro_spec": spec_name, "_spec": spec,
        })
        repro_files.append(spec_name)

    severity_matrix: dict[str, int] = {}
    for d in defects:
        severity_matrix[d["severity"]] = severity_matrix.get(d["severity"], 0) + 1

    report = {
        "report_version": "qa-report-v1", "target_url": target_url, "run_id": run_id,
        "duration_ms": verification.get("duration_ms", 0),
        "summary": {
            "total_verified": len(verified), "duplicates_merged": len(merged),
            "repro_count": len(repro_files),
            "dismissed_count": verification.get("summary", {}).get("dismissed_count", 0),
            "severity_matrix": severity_matrix,
        },
        "defects": [{k: v for k, v in d.items() if k != "_spec"} for d in defects],
        "duplicates_merged": merged,
        "dismissed_summary": {"count": verification.get("summary", {}).get("dismissed_count", 0)},
        "repro_files": repro_files,
    }
    report["_specs"] = {d["repro_spec"]: d["_spec"] for d in defects}
    emit(page_dir if page_dir is not None else _page_dir(plan), "report", "report.generated",
         {"run_id": run_id, **report["summary"]})
    return report


def _page_dir(plan: dict[str, Any]):
    from pathlib import Path
    return Path(plan.get("page_dir", ".")) if plan.get("page_dir") else Path(".")
