"""API interface tests — router-based FastAPI app over the services (TestClient)."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402

from bot.interfaces.api import app  # noqa: E402


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("QA_BOT_ARTIFACTS_DIR", str(tmp_path / "artifacts"))
    from bot.settings import get_settings
    get_settings.cache_clear()
    yield TestClient(app)
    get_settings.cache_clear()


def _crawl(client) -> str:
    r = client.post("/api/v2/crawl", json={"url": "https://example.com/login", "backend": "fake"})
    assert r.status_code == 201
    slug = r.json()["slug"]
    assert "/home/" not in slug
    return slug


def test_live_health_crawls(client: TestClient) -> None:
    assert client.get("/api/v2/live").json() == {"status": "live"}
    assert client.get("/api/v2/health").json()["status"] == "healthy"
    assert client.get("/api/v2/crawl").json() == []


def test_full_chain(client: TestClient) -> None:
    slug = _crawl(client)
    g = client.post("/api/v2/ground", json={"identifier": slug})
    assert g.json()["ok_count"] == 2

    p = client.post("/api/v2/plan", json={"identifier": slug})
    assert p.json()["test_cases_count"] == 1
    assert client.get(f"/api/v2/plan/{slug}").json()["plan_version"] == "qa-plan-v1"

    ex = client.post("/api/v2/execute", json={"identifier": slug})
    assert ex.json()["summary"]["total_cases"] == 1
    assert client.get(f"/api/v2/execute/{slug}").json()["execution_version"] == "qa-execution-v1"

    v = client.post("/api/v2/verify", json={"identifier": slug})
    assert "verified_findings" in v.json()

    rep = client.post("/api/v2/report", json={"identifier": slug})
    assert rep.json()["report_version"] == "qa-report-v1"
    assert "repro_specs" in rep.json()

    assert client.get("/api/v2/crawl").json()[0]["slug"] == slug


def test_artifacts_endpoints(client: TestClient) -> None:
    slug = _crawl(client)
    mani = client.get(f"/api/v2/artifacts/{slug}/manifest").json()
    assert "phases" in mani and mani["phases"]["shared"]["exists"]
    assert client.get(f"/api/v2/artifacts/{slug}/planner-input").json()["schema_version"] == "planner-input-v1"
    assert client.get(f"/api/v2/artifacts/{slug}/sub-urls").status_code == 200
    assert client.get(f"/api/v2/artifacts/{slug}/file/../../../etc/passwd").status_code in (400, 404)


def test_errors_and_correlation(client: TestClient) -> None:
    r = client.post("/api/v2/plan", json={"identifier": "does_not_exist"})
    assert r.status_code == 404
    assert "error" in r.json()
    assert "X-Run-Id" in client.get("/api/v2/health").headers
    assert client.post("/api/v2/crawl", json={"url": "ftp://x", "backend": "fake"}).status_code == 422
    slug = _crawl(client)
    assert client.post("/api/v2/execute", json={"identifier": slug}).status_code == 409

