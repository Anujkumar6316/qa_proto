#!/usr/bin/env python3
"""
QA Bot v0.2 — Project Console (root entrypoint).

Run with no arguments to see the visual banner + live diagnostics.
Pipeline subcommands (crawl/ground/plan/execute/report/all) are delegated to
the `qa-bot` CLI (`bot.interfaces.cli`), so there is one implementation.

    python main.py                 # banner console
    python main.py --json          # diagnostics as JSON
    python main.py all <url>       # crawl -> ground -> plan
    python main.py report <mani>   # execute -> verify -> report
    python main.py test            # run the pytest suite
"""

from __future__ import annotations

import logging
import sys

# Subcommands owned by the typer CLI in bot.interfaces.cli.
_PIPELINE_COMMANDS = {"crawl", "ground", "plan", "execute", "report", "all"}


def _configure_logging() -> None:
    """Single logging setup for every entrypoint (banner + delegated CLI).

    Level comes from QA_BOT_LOG_LEVEL; handlers go to stderr so stdout stays
    clean for `--json` output and rich rendering.
    """
    from bot.settings import get_settings

    level = getattr(logging, get_settings().LOG_LEVEL.upper(), logging.INFO)
    logging.basicConfig(
        level=level,
        stream=sys.stderr,
        format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
    )
    if get_settings().DEBUG:
        logging.getLogger("bot").setLevel(logging.DEBUG)


def _run_pipeline() -> int:
    """Delegate a pipeline subcommand to the qa-bot CLI (reads sys.argv)."""
    from bot.interfaces.cli import app

    try:  # typer parses sys.argv and dispatches; exits via SystemExit on error
        app()
    except SystemExit as exc:
        code = exc.code
        return int(code) if isinstance(code, int) else (0 if code is None else 1)
    return 0


def _run_tests() -> int:
    import pytest

    return pytest.main(["tests"])


def main() -> int:
    argv = sys.argv[1:]
    _configure_logging()

    # 1. Pipeline subcommands -> qa-bot CLI (single source of truth).
    if argv and argv[0] in _PIPELINE_COMMANDS:
        return _run_pipeline()

    # 2. Banner console (default) + a couple of local conveniences.
    import argparse

    from bot.main import render_project_banner

    parser = argparse.ArgumentParser(
        prog="main.py",
        description="QA Bot v0.2 — Project Console & Banner. "
                    "Pipeline: `python main.py <crawl|ground|plan|execute|report|all> ...`",
    )
    parser.add_argument("--banner", action="store_true", help="Display the project visual banner")
    parser.add_argument("--json", action="store_true", help="Output system diagnostics as JSON")
    parser.add_argument("command", nargs="?", choices=["info", "test"], help="info | test")
    args = parser.parse_args(argv)

    if args.command == "test":
        return _run_tests()
    # `info` and the default (no command / --banner) both render the banner.
    render_project_banner(json_mode=args.json or args.command == "info")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
