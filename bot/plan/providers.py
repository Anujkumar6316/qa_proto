"""Plan providers — real LLM only (fail-closed). No mock: a missing model is a hard error.

The default provider is an OpenAI-compatible chat model driven through
`langchain-openai` (ChatOpenAI). Configuration, in priority order:

1. Per-request overrides (Studio "Model override" / API `provider`+`model` fields).
2. `.env` defaults (`QA_BOT_LLM_BASE_URL`, `QA_BOT_LLM_API_KEY`, `QA_BOT_PLANNER_MODEL`).

Any failure (package missing, no key, network/auth error, unparseable output) raises
a clear message — the pipeline never silently falls back to canned plans.
"""

from __future__ import annotations

import json
import re
from typing import Any

from bot.ai_ml.prompts import load_prompt, load_strategy
from bot.execute.driver import KNOWN_ACTIONS
from bot.settings import get_settings

DEFAULT_MODEL = "gpt-4o-mini"
_JSON_BLOCK_RE = re.compile(r"```(?:json)?\s*(.*?)```", re.DOTALL)


class PlanProviderError(RuntimeError):
    """Raised when the planner cannot produce a plan. Always surfaced to the caller."""


def _extract_json(text: str) -> dict[str, Any]:
    """Parse a qa-plan JSON object out of a model reply (raw or fenced). Raises on miss."""
    candidates = [text.strip()] + [b.strip() for b in _JSON_BLOCK_RE.findall(text)]
    for cand in reversed(candidates):
        if not cand.startswith("{"):
            start, end = cand.find("{"), cand.rfind("}")
            if start == -1 or end <= start:
                continue
            cand = cand[start:end + 1]
        try:
            data = json.loads(cand)
        except json.JSONDecodeError:
            continue
        if isinstance(data, dict):
            return data
    raise PlanProviderError(
        f"Planner reply was not valid JSON qa-plan (first 200 chars): {text[:200]!r}")


class OpenAICompatPlanProvider:
    """Grounded planner via any OpenAI-compatible endpoint (OpenAI, Azure-style gateways,
    Ollama/vLLM/LiteLLM with a base_url). Uses langchain-openai's ChatOpenAI."""

    def __init__(self, *, model: str | None = None, api_key: str | None = None,
                 base_url: str | None = None, strategy: str = "comprehensive",
                 temperature: float = 0.0, timeout_s: int | None = None,
                 max_retries: int | None = None) -> None:
        settings = get_settings()
        self.model = (model or settings.PLANNER_MODEL or "").strip() or DEFAULT_MODEL
        self.api_key = (api_key if api_key is not None else settings.LLM_API_KEY).strip()
        self.base_url = (base_url if base_url is not None else settings.LLM_BASE_URL).strip() or None
        self.strategy = strategy
        self.temperature = temperature
        self.timeout_s = timeout_s if timeout_s is not None else settings.LLM_TIMEOUT_S
        self.max_retries = max_retries if max_retries is not None else settings.LLM_MAX_RETRIES

    @property
    def name(self) -> str:
        return f"openai-compatible:{self.model}"

    def _chat(self):
        try:
            from langchain_openai import ChatOpenAI
        except ImportError as exc:
            raise PlanProviderError(
                "langchain-openai is not installed. Install it with "
                "`pip install -e '.[llm]'` (or `pip install langchain-openai`).") from exc
        if not self.api_key:
            raise PlanProviderError(
                "No LLM API key configured. Set QA_BOT_LLM_API_KEY in .env "
                "(see .env.example) or provide a model override.")
        try:
            return ChatOpenAI(model=self.model, api_key=self.api_key,
                              base_url=self.base_url, temperature=self.temperature,
                              timeout=self.timeout_s, max_retries=self.max_retries)
        except Exception as exc:
            raise PlanProviderError(f"Could not initialise ChatOpenAI ({self.name}): {exc}") from exc

    def _build_messages(self, planner_input: dict[str, Any]) -> tuple[str, str]:
        system = load_prompt("planner/system.md")
        try:
            strategy_guide = load_strategy(self.strategy)
        except FileNotFoundError as exc:
            raise PlanProviderError(f"Unknown planner strategy '{self.strategy}': {exc}") from exc
        template = load_prompt("planner/user_template.md")
        # The templates contain literal JSON/JS examples with braces (e.g. `${x}`),
        # which str.format would misread as placeholders — substitute tokens instead.
        subs = {
            "strategy": self.strategy,
            "strategy_guide": strategy_guide,
            "planner_input": json.dumps(planner_input, indent=2),
            "journey_section": "",
            "step_actions": ", ".join(sorted(KNOWN_ACTIONS)),
            "plan_version": "qa-plan-v1",
        }
        user = template
        for key, val in subs.items():
            user = user.replace("{" + key + "}", val)
        return system, user

    def generate(self, planner_input: dict[str, Any]) -> dict[str, Any]:
        system, user = self._build_messages(planner_input)
        chat = self._chat()
        try:
            reply = chat.invoke([("system", system), ("human", user)])
        except PlanProviderError:
            raise
        except Exception as exc:
            raise PlanProviderError(
                f"LLM call failed ({self.name}, base_url={self.base_url or 'https://api.openai.com/v1'}): "
                f"{type(exc).__name__}: {exc}. "
                "Check QA_BOT_LLM_API_KEY / QA_BOT_LLM_BASE_URL / QA_BOT_PLANNER_MODEL in .env.") from exc
        text = getattr(reply, "content", "")
        if isinstance(text, list):  # multimodal content blocks
            text = "".join(p.get("text", "") if isinstance(p, dict) else str(p) for p in text)
        plan = _extract_json(str(text))
        plan.setdefault("plan_version", "qa-plan-v1")
        plan.setdefault("target_url", planner_input.get("page", {}).get("url", ""))
        plan.setdefault("test_suite", f"llm-{self.strategy}")
        plan.setdefault("thought_analysis", "")
        plan["_provider_model"] = self.model  # provenance for Studio/API display
        return plan


def build_plan_provider(strategy: str = "comprehensive", *, model: str | None = None,
                        base_url: str | None = None, api_key: str | None = None
                        ) -> OpenAICompatPlanProvider:
    """Single construction seam used by Studio/API/CLI. Fail-closed: no mock fallback."""
    return OpenAICompatPlanProvider(strategy=strategy, model=model or None,
                                    base_url=base_url or None, api_key=api_key or None)
