"""Exact-key dedupe for verified findings. Highest confidence wins; merge ledger."""

from __future__ import annotations

from typing import Any


def _norm(value: Any) -> str:
    return value.strip().casefold() if isinstance(value, str) else ""


def _confidence(finding: dict[str, Any]) -> float:
    try:
        return float(finding.get("confidence", 0.0) or 0.0)
    except (TypeError, ValueError):
        return 0.0


def dedupe_key(finding: dict[str, Any], target_url: str = "") -> str:
    return " | ".join([
        _norm(finding.get("title")),
        _norm(finding.get("page_url") or finding.get("target_url") or target_url),
        _norm(finding.get("target_ref")),
        str(finding.get("step_index", "")),
        _norm(finding.get("failure_class")),
    ])


def dedupe_verified_findings(verified: list[dict[str, Any]],
                             target_url: str = "") -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    seen: dict[str, dict[str, Any]] = {}
    merged: list[dict[str, Any]] = []
    for finding in verified:
        key = dedupe_key(finding, target_url)
        if key in seen:
            incumbent = seen[key]
            if _confidence(finding) > _confidence(incumbent):
                merged.append({"merged_id": incumbent.get("id", ""), "into_id": finding.get("id", ""), "key": key})
                seen[key] = finding
            else:
                merged.append({"merged_id": finding.get("id", ""), "into_id": incumbent.get("id", ""), "key": key})
        else:
            seen[key] = finding
    return list(seen.values()), merged
