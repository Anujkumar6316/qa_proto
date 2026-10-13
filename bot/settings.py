"""Single settings source for QA Bot v0.2. Fail-closed, namespaced QA_BOT_*."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """All runtime configuration. One object, no drift."""

    model_config = SettingsConfigDict(
        env_prefix="QA_BOT_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    PROJECT_NAME: str = "QA Bot v0.2"
    VERSION: str = "0.2.0"
    API_V2_PREFIX: str = "/api/v2"
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"

    # Storage — relative paths anchor to the package root (CWD-independent).
    ARTIFACTS_DIR: Path = Path("artifacts")

    # Browser budgets
    ACTION_TIMEOUT_MS: int = 5000
    NAV_TIMEOUT_MS: int = 30000
    CASE_BUDGET_S: int = 60
    RUN_BUDGET_S: int = 600
    SESSION_GATE_ATTEMPTS: int = 3
    SESSION_GATE_TIMEOUT_MS: int = 30000

    # Tunnel profile (slow ephemeral dev links)
    TUNNEL_ACTION_TIMEOUT_MS: int = 10000
    TUNNEL_NAV_TIMEOUT_MS: int = 60000
    TUNNEL_SESSION_GATE_TIMEOUT_MS: int = 60000
    TUNNEL_CASE_BUDGET_S: int = 120

    # Sandbox gate — fail-closed by default.
    SANDBOX_OPEN_GATE: bool = False
    SANDBOX_ALLOWED_DOMAINS: str = ""
    ALLOW_PRIVATE_HOSTS: bool = False

    # Step budgets
    MAX_STEPS_SINGLE: int = 6
    MAX_STEPS_JOURNEY: int = 12

    # Planner / judge
    PLANNER_PROVIDER: str = "mock"
    PLANNER_MODEL: str = "mock"
    LLM_BASE_URL: str = ""
    LLM_API_KEY: str = ""
    LLM_TIMEOUT_S: int = 30
    LLM_MAX_RETRIES: int = 1

    # Uploads
    MAX_UPLOAD_BYTES: int = 10 * 1024 * 1024

    def resolved_artifacts_dir(self) -> Path:
        """Absolute, created artifact root. Single choke-point.

        Relative ARTIFACTS_DIR anchors to the package root (QA_v0.2/), NOT the
        current working directory — so the bot behaves identically from any CWD.
        """
        raw = self.ARTIFACTS_DIR
        if not raw.is_absolute():
            package_root = Path(__file__).resolve().parent.parent  # .../QA_v0.2
            raw = package_root / raw
        p = raw.expanduser().resolve()
        p.mkdir(parents=True, exist_ok=True)
        return p


@lru_cache
def get_settings() -> Settings:
    return Settings()
