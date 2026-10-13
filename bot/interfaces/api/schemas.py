"""Shared request/response DTOs for the v0.2 API (mirrors the root project's schemas)."""

from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


# ---- common ----
class ErrorDetail(BaseModel):
    code: str
    message: str
    details: Optional[Any] = None


class ErrorEnvelope(BaseModel):
    error: ErrorDetail
    run_id: Optional[str] = None


# ---- crawl ----
class CrawlRequest(BaseModel):
    url: str = Field(..., description="Target http(s) URL to crawl (single page)")
    scope: Literal["all", "forms", "catalog", "navigation"] = "all"
    backend: Literal["fake", "playwright"] = "fake"
    objective: str = ""
    force: bool = False
    allow_private: bool = False


class CrawlResponse(BaseModel):
    run_id: str
    status: str = "completed"
    base_url: str
    slug: str
    total_pages_crawled: int = 1
    components_count: int = 0
    manifest: dict[str, Any]


class CrawlListItem(BaseModel):
    slug: str
    run_id: Optional[str] = None
    base_url: Optional[str] = None
    components_count: int = 0


# ---- plan ----
class PlanRequest(BaseModel):
    identifier: str = Field(..., description="Crawl slug or run_id")
    strategy: str = "comprehensive"
    provider: Optional[str] = None
    model: Optional[str] = None
    force: bool = False


class PlanResponse(BaseModel):
    status: str = "completed"
    plan_version: str
    slug: str
    run_id: str
    target_url: str
    test_suite: str
    thought_analysis: str
    test_cases_count: int
    test_cases: list[dict[str, Any]] = Field(default_factory=list)
    plan_ref: str


# ---- execute / verify / report ----
class ExecuteRequest(BaseModel):
    identifier: str
    sandbox: bool = False
    backend: Literal["fake", "playwright"] = "fake"


class ReportRequest(BaseModel):
    identifier: str
    backend: Literal["fake", "playwright"] = "fake"


class IdentifierRequest(BaseModel):
    """Body for phase endpoints that run on an existing crawl (ground, verify)."""
    identifier: str
    backend: Literal["fake", "playwright"] = "fake"
