"""Ingest boundary — the only place that touches uploads or external URLs."""

from __future__ import annotations

from bot.ingest.files import IngestedFile, ingest_upload
from bot.ingest.urls import canonicalize_url

__all__ = ["IngestedFile", "canonicalize_url", "ingest_upload"]
