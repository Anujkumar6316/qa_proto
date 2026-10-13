"""Event log — one JSON line per event, run-relative, append-only."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from bot.ids import safe_join

EVENTS_FILENAME = "events.jsonl"


def emit(run_dir: Path, phase: str, event: str, attrs: dict[str, Any] | None = None,
         artifacts: dict[str, str] | None = None) -> None:
    """Append one event line under `<run_dir>/events.jsonl`. Never raises."""
    try:
        path = safe_join(run_dir, EVENTS_FILENAME)
        record = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "phase": phase,
            "event": event,
            "attrs": attrs or {},
            "artifacts": artifacts or {},
        }
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    except Exception:
        pass


def read_events(run_dir: Path) -> list[dict[str, Any]]:
    try:
        path = safe_join(run_dir, EVENTS_FILENAME)
        if not path.exists():
            return []
        return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    except Exception:
        return []
