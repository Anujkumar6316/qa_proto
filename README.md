# QA Bot v0.2 — Standalone Autonomous QA Pipeline

> **Standalone. Zero legacy imports.** One package (`bot`), Phases 1–6 live, fail-closed by design.
> Point it at a URL → get an evidence-backed, grounded QA report.

**Who this is for:** a QA analyst or developer who wants to point the tool at a URL and get
defect findings that survived an adversarial re-check — no hallucinated elements, no false positives.

## Status at a glance

| Phase | State | What it does | Needs a key? |
|---|---|---|---|
| 1. Crawl | ✅ Live | URL → `planner-input-v1` inventory via Playwright-native driver | No |
| 2. Ground | ✅ Live | Schema + box + folds + files grounding audit | No |
| 3. Plan | ✅ Live | Grounded `qa-plan-v1/v2` with anti-hallucination gate; `mock` provider free/offline | No (mock) |
| 4. Execute | ✅ Live | Bounded browser loop (max 6/12 steps, destructive-action guard) | No |
| 5. Verify | ✅ Live | Evidence-required gate: isolated replay + judge (kills false positives) | No (default judge) |
| 6. Report | ✅ Live | Dedupe + runnable Playwright repros + client report | No |

**Key promise:** Phases 1–2 run fully locally with zero cost. You only spend LLM money in Phase 3/5,
and only after Phase 2 proves the inventory is trustworthy.

## Install

```bash
cd QA_v0.2
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"          # core + pytest
pip install -e ".[browser]"      # Playwright (real crawling/execution)
playwright install --with-deps chromium
```

## Configure

```bash
cp .env.example .env
```

Everything is namespaced `QA_BOT_*`. The defaults are safe: `PLANNER_PROVIDER=mock` (free/offline),
sandbox gate **fail-closed**, SSRF gate blocks loopback/private hosts. See `.env.example`.

## First run — happy path

```bash
qa-bot all https://example.com/login          # crawl → ground → plan (fake backend, offline)
qa-bot crawl https://example.com/login --backend fake
qa-bot execute <path-to-site_manifest.json>
qa-bot report <path-to-site_manifest.json>    # execute → verify → report
qa-bot info --json                            # machine-readable diagnostics
```

Or the visual console:

```bash
python -m bot.main            # rich banner + live config
python -m bot.main --json     # same data as JSON
```

Run the pipeline against a real browser:

```bash
qa-bot crawl https://example.com/login --backend playwright
```

## Repo layout

```text
QA_v0.2/
  bot/                        # single package root — runtime + model layer
    main.py                   # rich banner console
    phases.py                 # phase status (single source of truth)
    settings.py               # one Settings, QA_BOT_* prefix, abs artifacts root
    ids.py                    # safe_join / SSRF / slug validators (fail-closed)
    events.py                 # append-only run-relative event log
    artifacts.py              # shared phase-dir names & canonical artifact refs
    ingest/                   # THE upload boundary — bytes in, run-relative ref out
    contracts/                # frozen schemas (planner-input-v1, qa-plan-v1/v2, execution, verification, report)
    crawl/  ground/  plan/  execute/  verify/  report/
    ai_ml/                    # model layer — prompts, providers, tasks, evaluation
      prompts/                # one prompt per named file
      providers/  tasks/  common/  config/  evaluation/
    interfaces/cli.py         # qa-bot CLI (thin shell over services)
  tests/                      # deterministic, no network
  pyproject.toml  .env.example
```

## Design invariants

- **Isolation.** Zero imports from any legacy `core/`/`api/`/`qa_studio*`/`planner/`/`qa_harness/`.
- **Path discipline.** One resolved artifact root; every join goes through `safe_join`; responses
  return run-relative refs — absolute host paths never leak.
- **Upload discipline.** `bot/ingest` is the only code that touches uploads. Bytes in, never a client
  path. (This is the fix for the `/home/.../Book 12.xlsx` class of bugs.)
- **Fail-closed.** Empty components raise; unknown actions raise; hallucinated `@eN` refs rejected;
  sandbox closed by default.
- **Layered.** Runtime (`crawl/execute/verify/...`) may call `bot.ai_ml.tasks.*`; the model layer
  never imports the browser driver, Playwright, or API routing.

## Commands cheat sheet

| What you want | Command |
|---|---|
| Banner / diagnostics | `python -m bot.main` |
| Full offline chain | `qa-bot all <url>` |
| Crawl one page | `qa-bot crawl <url> [--backend fake\|playwright]` |
| Ground audit | `qa-bot ground <manifest>` |
| Plan | `qa-bot plan <manifest>` |
| Execute | `qa-bot execute <manifest> [--sandbox]` |
| Verify + report | `qa-bot report <manifest>` |
| Test suite | `qa-bot test` |
| JSON diagnostics | `qa-bot info --json` |
| **REST API** | `uv run poe api` → http://127.0.0.1:8000/api/v2/docs |
| **Studio UI** | `uv run poe studio` → http://127.0.0.1:7860 |
| **Both servers** | `uv run poe serve` |

## Servers (poethepoet)

```bash
uv run poe api        # FastAPI REST API on :8000
uv run poe api-dev    # API with hot-reload
uv run poe studio     # Gradio Studio on :7860
uv run poe serve      # Studio (:7860) + API (:8000) together
```

## Documentation

Deep docs live in [`docs/`](docs/): [Architecture](docs/ARCHITECTURE.md) ·
[Phases & Contracts](docs/PHASES.md) · [API](docs/API.md) · [CLI](docs/CLI.md) ·
[Configuration](docs/CONFIGURATION.md) · [Prompts](docs/PROMPTS.md) · [Testing](docs/TESTING.md).

## Troubleshooting

| Symptom | Fix |
|---|---|
| `playwright` import error | `pip install -e ".[browser]"` then `playwright install chromium` |
| URL host blocked | Loopback/private hosts are blocked by default; set `QA_BOT_ALLOW_PRIVATE_HOSTS=true` for local dev |
| Destructive action blocked | Sandbox gate is fail-closed; pass `--sandbox` or set `QA_BOT_SANDBOX_OPEN_GATE=true` |
| Planner needs a key | Default `mock` provider is free; set `QA_BOT_PLANNER_PROVIDER` + `QA_BOT_LLM_*` for a real model |

