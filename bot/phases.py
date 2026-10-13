"""Single source of truth for pipeline phase status (v0.2)."""

from __future__ import annotations

PHASE_STATUS: dict[str, str] = {
    "phase_1_crawl": "live",
    "phase_2_ground": "live",
    "phase_3_plan": "live",
    "phase_4_execute": "live",
    "phase_5_verify": "live",
    "phase_6_report": "live",
}
