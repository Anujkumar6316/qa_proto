"""Crawl + normalizer + full-chain tests. FakeDriver only — no network."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from bot.crawl import FakeDriver, run_crawl  # noqa: E402
from bot.ground import run_ground  # noqa: E402
from bot.plan import run_plan  # noqa: E402
from bot.crawl.normalizer import normalize_snapshot  # noqa: E402


def test_normalize_maps_roles_and_refs() -> None:
    snap = {"url": "https://x.com", "title": "X", "components": [
        {"ref": "@e1", "role": "a", "name": "Home", "box": [0, 0, 10, 10]},
        {"ref": "bogus", "role": "input", "name": "Search", "type": "search", "box": [0, 0, 10, 10]},
    ]}
    out = normalize_snapshot(snap, url="https://x.com", objective="o")
    assert out["schema_version"] == "planner-input-v1"
    roles = {c["ref"]: c["role"] for c in out["components"]}
    assert roles["@e1"] == "link" and roles["@e2"] == "searchbox"
    from bot.ground import validate_contract
    assert validate_contract(out) == []


def test_run_crawl_contract(tmp_path: Path) -> None:
    manifest = run_crawl("https://example.com/login", tmp_path, backend="fake", run_id="abcdef01")
    assert manifest["run_id"] == "abcdef01"
    assert manifest["backend"] == "fake"
    page = manifest["pages"][0]
    assert page["slug"] == "example_com__login"
    # Every artifact ref must be run-relative, never absolute
    for ref in page["artifacts"].values():
        assert not Path(ref).is_absolute() and "/home/" not in ref
    planner = json.loads((tmp_path / "example_com__login" / "pages" / "example_com__login" / "shared" / "planner_input.json").read_text())
    assert len(planner["components"]) == 2


def test_fake_driver_open_snapshot_close() -> None:
    import asyncio

    drv = FakeDriver()

    async def _go() -> dict:
        opened = await drv.open("https://example.com")
        snap = await drv.snapshot()
        await drv.close()
        return {"opened": opened, "snap": snap}

    out = asyncio.run(_go())
    assert out["opened"]["ready"] is True
    assert out["snap"]["components"][0]["ref"] == "@e1"
    assert drv.opened == 1 and drv.closed == 1


def test_crawl_rejects_private_host(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="blocked"):
        run_crawl("http://localhost:9999/x", tmp_path, backend="fake")
    assert not list(tmp_path.glob("**/site_manifest.json"))


def test_unknown_backend_fails_closed(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="Unknown crawl backend"):
        run_crawl("https://example.com", tmp_path, backend="selenium")


def test_full_chain_crawl_ground_plan(tmp_path: Path) -> None:
    manifest = run_crawl("https://example.com/login", tmp_path, backend="fake")
    page_dir = tmp_path / "example_com__login" / "pages" / "example_com__login"

    ground, _ = run_ground(page_dir, run_id="abcdef01")
    assert ground.ok_count == 2

    plan, plan_path = run_plan(page_dir, run_id="abcdef01")
    assert plan["test_cases"][0]["id"] == "TC_001"
    assert plan_path.parent.name == "phase_3_plan"

    events = [json.loads(l) for l in (page_dir / "events.jsonl").read_text().splitlines()]
    phases = [e["phase"] for e in events]
    assert phases == ["crawl", "ground", "plan"]
