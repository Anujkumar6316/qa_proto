"""Crawl layer — BrowserDriver seam, normalizer, fail-closed service."""

from __future__ import annotations

from bot.crawl.browser import BrowserDriver
from bot.crawl.fake_driver import FakeDriver
from bot.crawl.normalizer import normalize_component, normalize_snapshot
from bot.crawl.playwright_driver import PlaywrightDriver
from bot.crawl.service import run_crawl

__all__ = [
    "BrowserDriver", "FakeDriver", "PlaywrightDriver",
    "normalize_component", "normalize_snapshot", "run_crawl",
]
