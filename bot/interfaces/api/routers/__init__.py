"""API routers — one module per phase, mirroring the root project's v1 router set."""

from __future__ import annotations

from bot.interfaces.api.routers import (
    artifacts, crawl, execute, ground, health, plan, report, verify,
)

__all__ = ["artifacts", "crawl", "execute", "ground", "health", "plan", "report", "verify"]
