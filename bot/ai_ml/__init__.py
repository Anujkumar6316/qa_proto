"""Model layer (ai_ml) — prompts, providers, tasks, validation, evaluation.

Boundary (see ARCHITECTURE.md): this subpackage MUST NOT import the browser
driver, Playwright, FastAPI routes, or run orchestration from `bot`. The runtime
(`bot.crawl/execute/verify/...`) may call into `bot.ai_ml.tasks.*`; never the
reverse. One importable package root: `bot`.
"""
