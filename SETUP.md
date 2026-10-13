# QA Bot v0.2 — Setup & Run Guide

Standalone autonomous QA pipeline: point it at a URL and get an evidence-backed,
grounded QA report (crawl → ground → plan → execute → verify → report).

---

## 1. Prerequisites

| Requirement | Version / Notes |
|---|---|
| Python | **3.12+** (`requires-python = ">=3.12"` in `pyproject.toml`) |
| pip | bundled with Python 3.12, or upgrade: `python -m pip install --upgrade pip` |
| uv *(optional)* | recommended fast installer + task runner (`uv run poe ...`) |
| Git | for cloning the repo |
| OS browser deps | Linux needs system libs for Chromium (handled by `playwright install --with-deps`) |

Verify Python first:

```bash
python3 --version   # must be 3.12 or newer
```

---

## 2. Installation

### Option A — pip + requirements.txt (simple)

```bash
cd QA_v0.2                                   # repo root
python -m venv .venv
source .venv/bin/activate                    # Windows: .venv\Scripts\activate

pip install -r requirements.txt              # all runtime deps + extras (pinned to uv.lock)
```

### Option B — editable install with extras (recommended for development)

```bash
python -m venv .venv && source .venv/bin/activate

pip install -e ".[dev]"                      # core + pytest (offline/fake backend works)
pip install -e ".[browser]"                  # Playwright (real crawling/execution)
pip install -e ".[llm]"                      # httpx (real LLM planner providers)
pip install -e ".[api]"                      # FastAPI + uvicorn REST server
pip install -e ".[studio]"                   # Gradio Studio UI

# Or everything at once:
pip install -e ".[browser,llm,api,studio,dev]"
```

### Option C — uv (fastest, lockfile-exact)

```bash
uv sync --extra browser --extra llm --extra api --extra studio --extra dev
# or simply: uv sync --all-extras
```

### Browser binaries (required for real crawling/execution)

```bash
playwright install --with-deps chromium       # Linux/macOS; adds system libraries
# If you used uv:  uv run playwright install --with-deps chromium
```

> Skip this if you only use the offline `fake` backend (`qa-bot all <url>` default).

---

## 3. Configuration

```bash
cp .env.example .env
```

All settings are namespaced `QA_BOT_*`. Defaults are safe and require no keys:

| Key | Default | Meaning |
|---|---|---|
| `QA_BOT_PLANNER_PROVIDER` | `mock` | Free/offline planner. Set to a real provider + `QA_BOT_LLM_*` keys to spend tokens |
| `QA_BOT_ALLOW_PRIVATE_HOSTS` | `false` | SSRF gate is fail-closed; set `true` only for local-dev targets |
| `QA_BOT_RESOLVE_HOSTS` | `true` | DNS-resolve targets and block private answers (disable for offline demos) |
| `QA_BOT_ARTIFACTS_DIR` | `artifacts` | Relative paths anchor to the package root |
| `QA_BOT_LOG_LEVEL` | `INFO` | `DEBUG \| INFO \| WARNING \| ERROR` |

Browser budgets, step limits, and tunnel profiles are documented inline in `.env.example`.

---

## 4. Verify the install

```bash
python main.py                # rich banner + live diagnostics
qa-bot info --json            # machine-readable diagnostics
pytest                        # deterministic test suite (no network)
```

Expected: banner renders, JSON prints without errors, tests pass.

---

## 5. Running the pipeline

### CLI (`qa-bot`)

```bash
# Full offline chain (fake backend, zero cost): crawl → ground → plan
qa-bot all https://quotes.toscrape.com/

# Real browser crawl
qa-bot crawl https://the-internet.herokuapp.com/login --backend playwright

# Ground audit / plan / execute / verify+report (manifest from a prior crawl)
qa-bot ground artifacts/<run-dir>/site_manifest.json
qa-bot plan   artifacts/<run-dir>/site_manifest.json
qa-bot execute artifacts/<run-dir>/site_manifest.json [--sandbox]
qa-bot report  artifacts/<run-dir>/site_manifest.json     # execute → verify → report

# Whole demo flow over all built-in demo links
qa-bot demo
qa-bot demo --url https://quotes.toscrape.com/ --backend playwright

# Diagnostics
qa-bot info --json
qa-bot test
```

Safe demo URLs (read-only sandboxes): `https://httpbin.org/html`,
`https://quotes.toscrape.com/`, `https://the-internet.herokuapp.com/login`,
`https://example.com`. See `README.md` for real-app demo links.

### Servers (poethepoet via uv, or plain commands inside the venv)

| What | uv command | Equivalent | Endpoint |
|---|---|---|---|
| REST API | `uv run poe api` | `uvicorn bot.interfaces.api:app --host 127.0.0.1 --port 8000` | http://127.0.0.1:8000/api/v2/docs |
| API hot-reload | `uv run poe api-dev` | same + `--reload` | — |
| Studio UI | `uv run poe studio` | `python -m bot.interfaces.studio` | http://127.0.0.1:7860 |
| Both servers | `uv run poe serve` | — | both of the above |
| Banner | `uv run poe banner` | `python main.py` | — |
| Tests | `uv run poe test` | `pytest` | — |

---

## 6. Project layout (quick map)

```text
QA_v0.2/
  main.py                 # rich banner console entry
  bot/                    # single package root
    interfaces/cli.py     # qa-bot CLI
    interfaces/api.py     # FastAPI app
    interfaces/studio.py  # Gradio UI
    crawl/ ground/ plan/ execute/ verify/ report/   # phases 1–6
    ai_ml/                # prompts, providers, tasks, evaluation
    contracts/            # frozen schemas
  tests/                  # deterministic, no network
  pyproject.toml          # deps, extras, scripts, poe tasks
  requirements.txt        # pinned mirror of pyproject deps
  .env.example            # config template
  docs/                   # ARCHITECTURE, PHASES, API, CLI, CONFIGURATION, PROMPTS, TESTING
```

---

## 7. Troubleshooting

| Symptom | Fix |
|---|---|
| `playwright` import error | `pip install -e ".[browser]"` then `playwright install --with-deps chromium` |
| Browser launches but crashes on Linux | Re-run `playwright install --with-deps chromium` to install system libs |
| `qa-bot: command not found` | Activate the venv, or reinstall with `pip install -e .`; with uv use `uv run qa-bot ...` |
| Target URL host blocked | Loopback/private hosts blocked by default → set `QA_BOT_ALLOW_PRIVATE_HOSTS=true` (local dev only) |
| Destructive action blocked | Sandbox gate: pass `--sandbox` or set `QA_BOT_SANDBOX_OPEN_GATE=true` |
| Planner wants an API key | Default `mock` provider is free/offline; only set `QA_BOT_PLANNER_PROVIDER` + `QA_BOT_LLM_*` when you want a real model |
| Python version error on install | Project requires ≥ 3.12 — check `python3 --version` and recreate the venv |
| Port already in use | Change ports in the poe/uvicorn commands (`--port`) or stop the conflicting process |
