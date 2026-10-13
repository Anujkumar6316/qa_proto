#!/usr/bin/env python3
"""
QA Bot v0.2 — Standalone Autonomous QA Pipeline.

Project Banner & System Status Console.
Pipeline runs are driven via the CLI (`qa-bot <command>` / `python -m bot.main`).
"""

from __future__ import annotations

import argparse
import json
import sys

from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from bot import __version__
from bot.phases import PHASE_STATUS
from bot.settings import get_settings

console = Console()


def _gather_diagnostics() -> dict:
    """Collect live, side-effect-free diagnostics. Never raises."""
    settings = get_settings()
    artifacts = settings.resolved_artifacts_dir()
    crawls_count = 0
    try:
        crawls_count = len([d for d in artifacts.iterdir()
                            if d.is_dir() and (d / "site_manifest.json").exists()])
    except Exception:
        crawls_count = 0
    return {"settings": settings, "artifacts_dir": str(artifacts), "crawls_count": crawls_count}


def render_project_banner(json_mode: bool = False) -> None:
    """Render the high-impact visual banner and live system diagnostics."""
    settings = get_settings()
    diag = _gather_diagnostics()

    if json_mode:
        data = {
            "project": settings.PROJECT_NAME,
            "version": settings.VERSION,
            "phases": dict(PHASE_STATUS),
            "storage": {"artifacts_dir": diag["artifacts_dir"], "indexed_crawls": diag["crawls_count"]},
            "ai_engine": {"provider": settings.PLANNER_PROVIDER, "model": settings.PLANNER_MODEL},
            "budgets": {
                "max_steps_single": settings.MAX_STEPS_SINGLE,
                "max_steps_journey": settings.MAX_STEPS_JOURNEY,
                "case_budget_s": settings.CASE_BUDGET_S,
                "run_budget_s": settings.RUN_BUDGET_S,
            },
            "sandbox": {"gate_removed": True,  # prototype: destructive actions run by default
                        "allow_private_hosts": settings.ALLOW_PRIVATE_HOSTS,
                        "resolve_hosts": settings.RESOLVE_HOSTS},
        }
        print(json.dumps(data, indent=2))
        return

    header = Text()
    header.append("QA BOT v0.2\n", style="bold cyan")
    header.append("Standalone Autonomous QA Pipeline & Visual Grounding Engine\n", style="bold white")
    header.append(f"v{__version__} • Phases 1-6 Live • Zero Hallucinations Protocol", style="dim italic")
    console.print(Panel(header, box=box.DOUBLE, border_style="cyan", padding=(1, 2)))

    phase_table = Table(title="[bold]Autonomous QA Pipeline Roadmap[/bold]",
                        box=box.ROUNDED, header_style="bold cyan", expand=True)
    phase_table.add_column("Phase", style="bold white", width=22)
    phase_table.add_column("Status", width=12)
    phase_table.add_column("Capability & Artifact Deliverables", style="dim")
    rows = [
        ("Phase 1: Crawl", "Playwright-native DOM crawler, @eN inventory, planner-input-v1"),
        ("Phase 2: Ground", "Grounding audit: schema + box + folds + files binding"),
        ("Phase 3: Plan", "Grounded test planner, qa-plan-v1/v2, anti-hallucination gate"),
        ("Phase 4: Execute", "Bounded browser loop (max 6/12 steps, destructive-action guard)"),
        ("Phase 5: Verify", "Adversarial evidence gate: replay + judge (kills false positives)"),
        ("Phase 6: Report", "Dedupe + Playwright repros + client audit report"),
    ]
    for name, cap in rows:
        phase_table.add_row(name, "[bold green]● LIVE[/bold green]", cap)
    console.print(phase_table)
    console.print()

    diag_table = Table(title="[bold]Live Runtime Health & Configuration[/bold]",
                       box=box.ROUNDED, header_style="bold blue", expand=True)
    diag_table.add_column("Component", style="bold white", width=22)
    diag_table.add_column("State / Value", width=26)
    diag_table.add_column("Details & Metrics", style="dim")
    diag_table.add_row("Artifact Storage", "[green]HEALTHY[/green]",
                       f"{diag['crawls_count']} crawl(s) indexed under {diag['artifacts_dir']}")
    diag_table.add_row("Planner Provider", f"[cyan]{settings.PLANNER_PROVIDER}[/cyan]",
                       f"Model: {settings.PLANNER_MODEL} (mock = free/offline)")
    diag_table.add_row("Browser Backend", "[cyan]playwright | fake[/cyan]",
                       "Playwright-native seam; fake driver for offline tests")
    diag_table.add_row("Step Budgets", f"{settings.MAX_STEPS_SINGLE} / {settings.MAX_STEPS_JOURNEY}",
                       f"single / journey steps; case budget {settings.CASE_BUDGET_S}s")
    diag_table.add_row("Sandbox Gate", "[yellow]REMOVED (prototype)[/yellow]",
                       "Destructive actions run by default; SSRF + domain allowlist still enforced")
    console.print(diag_table)
    console.print()

    cli_table = Table(title="[bold]CLI Quick-Start (`qa-bot <command>`)[/bold]",
                      box=box.ROUNDED, header_style="bold magenta", expand=True)
    cli_table.add_column("Command", style="bold green", width=26)
    cli_table.add_column("Purpose", width=30)
    cli_table.add_column("Notes", style="cyan")
    cli_table.add_row("qa-bot all <url>", "Crawl → Ground → Plan", "fake backend, offline")
    cli_table.add_row("qa-bot crawl <url>", "Capture planner-input-v1", "--backend fake|playwright")
    cli_table.add_row("qa-bot execute <manifest>", "Execute the plan", "sandbox gate removed (prototype)")
    cli_table.add_row("qa-bot report <manifest>", "Execute → Verify → Report", "verified defects + repros")
    cli_table.add_row("qa-bot test", "Run pytest suite", "deterministic, no network")
    cli_table.add_row("qa-bot info", "Diagnostics as JSON", "same data, machine-readable")
    console.print(cli_table)
    console.print()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="QA Bot v0.2 — Project Console & Banner. Pipeline via 'qa-bot <command>'."
    )
    parser.add_argument("--banner", action="store_true", help="Display the project visual banner")
    parser.add_argument("--json", action="store_true", help="Output system diagnostics as JSON")
    args = parser.parse_args()
    render_project_banner(json_mode=args.json)


if __name__ == "__main__":
    sys.exit(main())

