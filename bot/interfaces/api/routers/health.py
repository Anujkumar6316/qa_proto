"""Health router."""

from __future__ import annotations

from fastapi import APIRouter

from bot import __version__
from bot.phases import PHASE_STATUS
from bot.interfaces.api.resolve import artifacts_root

router = APIRouter(tags=["Health"])


@router.get("/live", include_in_schema=False)
def live() -> dict[str, str]:
    return {"status": "live"}


@router.get("/health")
def health() -> dict:
    return {"status": "healthy", "version": __version__,
            "phases": dict(PHASE_STATUS), "artifacts_dir": str(artifacts_root())}
