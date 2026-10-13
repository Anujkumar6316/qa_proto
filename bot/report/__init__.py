"""Report package — dedupe, Playwright repro synthesis, client view. qa-report-v1."""

from __future__ import annotations

from bot.report.dedupe import dedupe_key, dedupe_verified_findings
from bot.report.repro import build_repro_spec
from bot.report.service import run_report

__all__ = ["build_repro_spec", "dedupe_key", "dedupe_verified_findings", "run_report"]
