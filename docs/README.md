# QA Bot v0.2 — Documentation

Detailed documentation for the standalone v0.2 pipeline. Start with the top-level
[`README.md`](../README.md) for install + first run; these pages go deeper.

## Contents

| Doc | What's inside |
|---|---|
| [ARCHITECTURE.md](ARCHITECTURE.md) | Layered design, package map, data flow, design invariants |
| [PHASES.md](PHASES.md) | The six phases in detail + frozen contracts |
| [API.md](API.md) | REST endpoint reference (`/api/v2/*`) with curl examples |
| [CLI.md](CLI.md) | `qa-bot` / `main.py` command reference |
| [CONFIGURATION.md](CONFIGURATION.md) | Every `QA_BOT_*` environment variable |
| [PROMPTS.md](PROMPTS.md) | The prompt library (`bot/ai_ml/prompts/`) |
| [TESTING.md](TESTING.md) | How the test suite is structured and run |

## 30-second mental model

```
URL ─▶ Crawl ─▶ planner-input-v1 ─▶ Ground ─▶ Plan ─▶ qa-plan-v1
                                       │
                              Execute ─▶ qa-execution-v1 (candidate findings)
                                       │
                               Verify ─▶ qa-verification-v1 (verified / dismissed)
                                       │
                               Report ─▶ qa-report-v1 (+ runnable .spec.ts repros)
```

Each phase is a service in `bot/<phase>/`. Three thin shells drive them:
`main.py`/`qa-bot` (CLI), `bot/interfaces/api.py` (REST), `bot/interfaces/studio.py` (Gradio).
The model layer `bot/ai_ml/` owns prompts, providers, and task validation — it never
touches the browser.
