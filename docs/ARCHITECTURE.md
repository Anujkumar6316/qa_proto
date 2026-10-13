# Architecture

QA Bot v0.2 is a **single Python package** (`bot`) with a strict layering. The whole
design exists to guarantee three properties: **isolation** (no legacy imports),
**path safety** (no absolute host paths leak, uploads are contained), and
**fail-closed correctness** (hallucinated elements and false positives are rejected
by construction).

## Layering

```
┌──────────────────────────────────────────────────────────────────────┐
│ INTERFACES (thin shells — zero pipeline logic)                        │
│   main.py · bot/interfaces/cli.py · api.py (FastAPI) · studio.py      │
│   Each one only calls services and renders results.                   │
├──────────────────────────────────────────────────────────────────────┤
│ SERVICES (one per phase — own the behavior)                           │
│   crawl/  ground/  plan/  execute/  verify/  report/                  │
│   Each: load → compute → persist artifact → emit event.               │
├──────────────────────────────────────────────────────────────────────┤
│ MODEL LAYER  bot/ai_ml/  (prompts, providers, tasks, evaluation)      │
│   Owns model calls + structured-output validation.                    │
│   MUST NOT import the browser driver, Playwright, or API routing.     │
│   The runtime (services) may call ai_ml.tasks.* — never the reverse.  │
├──────────────────────────────────────────────────────────────────────┤
│ FOUNDATIONS (shared, dependency-free)                                 │
│   settings.py · ids.py · events.py · contracts/ · ingest/             │
└──────────────────────────────────────────────────────────────────────┘
```

The dependency arrow only points **down**. `interfaces → services → {ai_ml, foundations}`.
`ai_ml` is a leaf with respect to the browser: nothing in `ai_ml/` imports `crawl`,
`execute`, `verify`, Playwright, or FastAPI.

## Package map

```
bot/
  main.py                 Rich banner console (project status)
  phases.py               PHASE_STATUS — single source of truth
  settings.py             Settings (pydantic-settings, QA_BOT_* prefix)
  ids.py                  safe_join, relative_ref, assert_safe_url, slug/ref/run_id
  events.py               append-only run-relative event log (events.jsonl)
  ingest/                 THE upload boundary — bytes in, run-relative ref out
  contracts/              Frozen JSON schemas + PROVENANCE.md
  crawl/    browser.py  normalizer.py  fake_driver.py  playwright_driver.py  service.py
  ground/   audit.py  service.py
  plan/     grounding.py  service.py  (MockPlanProvider + fail-closed gate)
  execute/  assertions.py  guardrails.py  driver.py  fake_driver.py  runner.py
  verify/   gate.py  replayer.py  judge.py  service.py
  report/   dedupe.py  repro.py  service.py
  ai_ml/    prompts/  providers/  tasks/  common/  config/  evaluation/
  interfaces/  cli.py  api.py  studio.py
```

## Data flow & artifacts

One crawl produces a run directory, and every phase writes its own subfolder. All
artifact references stored in `site_manifest.json` are **run-relative** — resolved
against the artifacts root at read time, never persisted as absolute host paths.

```
artifacts/
└── <slug>/                              # e.g. example_com__login
    ├── site_manifest.json               # run-relative refs to every artifact
    └── pages/<slug>/
        ├── events.jsonl                 # crawl → ground → plan → verify → report
        ├── shared/planner_input.json    # planner-input-v1 (SSOT contract)
        ├── phase_1_crawl/               # raw_snapshot.json, sub_urls.txt, screenshots/
        ├── phase_2_ground/grounding_audit.json
        ├── phase_3_plan/qa_plan.json    # qa-plan-v1 / qa-plan-v2
        ├── phase_4_execute/             # qa_execution.json
        ├── phase_5_verify/              # qa_verification.json
        └── phase_6_report/              # qa_report.json + *.spec.ts repros
```

## Design invariants (enforced, tested)

1. **Isolation.** `grep` for `core`/`api`/`qa_studio`/`planner`/`qa_harness` imports
   in `bot/` returns nothing. v0.2 is a clean room.
2. **Path discipline.** One resolved artifact root (`settings.resolved_artifacts_dir()`,
   anchored to the package root, not CWD). Every join goes through `ids.safe_join`,
   which raises if the result escapes the base. API/Studio responses carry
   `ids.relative_ref` values — absolute host paths never leave the process.
3. **Upload discipline.** `bot/ingest` is the *only* code that touches uploads.
   `ingest_upload(data: bytes, filename_hint, run_dir)` takes bytes, never a client
   path; it sniffs the type, caps the size, sanitizes the name, and stores under
   `uploads/`. This is the fix for the `/home/.../Book 12.xlsx` class of bugs.
4. **Fail-closed.** Empty `components` raises (no invented `@e1`); unknown actions
   raise; hallucinated `@eN` refs are rejected by the grounding gate; the sandbox
   gate is closed by default; SSRF blocks loopback/private hosts by default.
5. **Bounded execution.** Every test case is capped at `MAX_STEPS_SINGLE` (6) or
   `MAX_STEPS_JOURNEY` (12) steps; one browser session per case, always closed.
6. **No self-declared product bugs.** The executor classifies failures as
   `harness` / `guardrail_block` / `test-plan` / `server-error` / `unclassified`.
   Only evidence-backed, replay-reproduced candidates become `VERIFIED` defects.

## Driver seam

Both crawl and execute depend on a `Protocol`, not a backend:

- `crawl.browser.BrowserDriver` — `open` / `snapshot` / `close`
- `execute.driver.ExecDriver` — `goto` / `resolve` / `act` / `page_text` / `current_url` / `close`

Two implementations exist per seam: a deterministic `FakeDriver` (offline tests, the
default) and `PlaywrightDriver` (real browser). Swap via `--backend fake|playwright`
(CLI) or the `backend` field (API). No backend type leaks into the services.

## Failure classification contract

| `failure_class` | Meaning | Can become a product defect? |
|---|---|---|
| `unclassified` | Assertion mismatch, needs adjudication | Only after replay + judge |
| `harness` | Locator not found, navigation/driver failure | No |
| `guardrail_block` | Destructive action blocked by policy | No |
| `test-plan` | Malformed plan / step-budget exceeded | No |
| `server-error` | HTTP 5xx observed | Yes (genuine) |
| `blocked_bot` / `timeout` | Challenge page / budget | No |

The judge default dismisses anything non-`unclassified`/`server-error` and anything
that fails to reproduce in isolated replay. A custom judge (LLM) plugs into
`run_verification(judge=...)`; a single judge failure never loses the run.

