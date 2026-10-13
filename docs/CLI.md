# CLI Reference

Two entrypoints, one implementation:

- **`main.py`** (repo root) — banner console by default; delegates pipeline
  subcommands to the `qa-bot` CLI.
- **`qa-bot`** (installed script, or `python -m bot.interfaces.cli`) — the pipeline.

Both are thin shells over the same services — no duplicated logic.

## `main.py`

```bash
python main.py                 # rich banner + live diagnostics
python main.py --json          # diagnostics as JSON
python main.py info --json     # same as --json
python main.py test            # run the pytest suite
python main.py <subcommand> …  # delegated to qa-bot (see below)
```

## `qa-bot` commands

| Command | Purpose | Key options |
|---|---|---|
| `qa-bot crawl <url>` | Crawl one page → `planner-input-v1` | `--backend fake\|playwright`, `--out DIR` |
| `qa-bot ground <manifest>` | Grounding audit | — |
| `qa-bot plan <manifest>` | Generate a grounded plan (mock provider) | — |
| `qa-bot execute <manifest>` | Execute the plan | `--sandbox` |
| `qa-bot report <manifest>` | Execute → verify → report | — |
| `qa-bot all <url>` | Crawl → ground → plan in one shot | `--backend`, `--out DIR` |
| `qa-bot demo` | Run the whole flow over the built-in demo links | `--url <u>`, `--backend`, `--out DIR` |

`<manifest>` is the path to a crawl's `site_manifest.json` (e.g.
`artifacts/example_com__login/site_manifest.json`).

## Examples

```bash
# Offline full chain (fake backend, no network)
qa-bot all https://example.com/login

# Real browser crawl
qa-bot crawl https://example.com/login --backend playwright

# Drive later phases off the produced manifest
qa-bot execute artifacts/example_com__login/site_manifest.json
qa-bot report  artifacts/example_com__login/site_manifest.json

# Unlock destructive-action flows (sandbox gate is fail-closed by default)
qa-bot execute artifacts/example_com__login/site_manifest.json --sandbox

# Demo the whole flow over every built-in public demo link
qa-bot demo

# Demo one specific public link with a real browser
qa-bot demo --url https://the-internet.herokuapp.com/login --backend playwright
```

## Demo links

Built into `qa-bot demo` (`bot.interfaces.cli.DEMO_URLS`) — public, safe to test:

- `https://httpbin.org/html` — minimal single page (fastest smoke test)
- `https://quotes.toscrape.com/` — multi-page crawl, pagination, login form
- `https://the-internet.herokuapp.com/login` — auth flow + deliberate defects
- `https://example.com` — absolute-minimal crawl sanity check
- `https://demoqa.com/login` — form validation + known-bad elements

More options in the README's [Demo & test links](../README.md#demo--test-links) section
(`saucedemo.com`, `practicetest.automationtesting.in`, `katalyst-demo-cyi.netlify.app`).

## Task runner (poethepoet)

```bash
uv run poe --help        # list all tasks
uv run poe api           # FastAPI API on :8000
uv run poe api-dev       # API with hot-reload
uv run poe studio        # Gradio Studio on :7860
uv run poe serve         # Studio + API together
uv run poe banner        # rich banner
uv run poe info          # diagnostics JSON
uv run poe test          # pytest
```

## Exit codes

- `0` success.
- Non-zero from `test` (pytest's code) or when a service raises (bad URL → validation
  error, unknown slug → not found, grounding rejection → fail-closed).
