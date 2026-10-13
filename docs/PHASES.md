# Phases & Contracts

Six phases, each a service in `bot/<phase>/service.py`. Every phase reads the previous
phase's artifact and writes its own, emitting a run event. Contracts are frozen JSON
schemas in `bot/contracts/` (see `PROVENANCE.md`).

## Phase 1 — Crawl  (`bot/crawl/`)

**Input:** a URL. **Output:** `planner-input-v1` + `site_manifest.json`.

- `assert_safe_url` canonicalizes and blocks SSRF (loopback/private unless allowed).
- The `BrowserDriver` opens the page and snapshots interactive elements
  (`@eN` refs, roles, names, bounding boxes, stable selector `fingerprint`s).
- `normalizer.normalize_snapshot` maps raw roles (`a`→`link`, `input`+`type=search`→
  `searchbox`, …) into the frozen `planner-input-v1` shape and guarantees unique
  `@eN` refs.
- Backends: `fake` (deterministic, offline — the default) or `playwright` (real).

**Key functions:** `run_crawl(url, output_dir, *, backend, scope, objective, allow_private)`.

## Phase 2 — Ground  (`bot/ground/`)

**Input:** `planner_input.json`. **Output:** `grounding_audit.json`.

Two pure layers, no LLM, no browser:
- **Layer A — contract** (`validate_contract`): required keys, `schema_version`,
  non-empty `objective`/`page.url`/`components`.
- **Layer B — grounding** (`check_grounding`): ref format + duplicates, valid roles,
  box parseability + geometry (non-degenerate, within viewport), and on-disk fold
  bindings when screenshots exist. Issues bucketed as
  `validator / box / refs / folds / files`.

**Key functions:** `run_ground(page_dir) -> (GroundResult, audit_path)`.

## Phase 3 — Plan  (`bot/plan/`)

**Input:** `planner_input.json`. **Output:** `qa-plan-v1` / `qa-plan-v2`.

- `MockPlanProvider` produces one grounded happy-path case offline (free).
- `grounding.validate_plan_grounding` is the **anti-hallucination gate** — a plan is
  rejected unless: `plan_version` is valid; `test_cases` non-empty with unique ids;
  every case has ≥2 steps and a terminal assertion; every `target_ref` exists in the
  page's components; `target_selector` (if present) equals the registry fingerprint;
  `fill` values are concrete (no `test`/`foo`); `assert_attr` carries an `attribute`.
- Fail-closed: empty components raise before any provider call.

**Key functions:** `run_plan(page_dir, provider=None) -> (plan, plan_path)`.
A real provider plugs in by implementing `PlanProvider.generate(planner_input) -> dict`
(see [PROMPTS.md](PROMPTS.md) for the prompts it would use).

**Studio Phase 3 tab layout:** the "Phase 3 — Plan" tab contains two separate sub-tabs:
- **Plan** — strategy picker, model dropdown, custom model id, credential overrides,
  generate button, and plan outputs (summary/cards/table/JSON).
- **Model Catalog** — read-only table of every selectable model, loaded from
  `QA_BOT_MODEL_CATALOG` in `.env` (comma-separated; includes Ollama models such as
  `ollama/llama3.1`, served via the OpenAI-compatible endpoint
  `http://localhost:11434/v1`). The first row is the **Default** option.
- **Default option → loads the model from `.env`:** choosing "(default — from .env)"
  in the model dropdown (or leaving it blank with no custom id) sends no override, so
  planning falls back to `QA_BOT_PLANNER_MODEL` from `.env`. Selection order:
  custom model id box → catalog dropdown → `.env` default.

## Phase 4 — Execute  (`bot/execute/`)

**Input:** `qa_plan.json`. **Output:** `qa-execution-v1` with candidate findings.

- One `ExecDriver` session per test case, always closed in `finally`.
- `guardrails.evaluate_action` blocks destructive/financial actions (scans name, role,
  value, **and selector**) and any off-allowlist navigation — regardless of sandbox.
- `validate_step_budget` caps steps (6 single / 12 journey).
- `assertions.*` are deterministic evaluators for the five assert actions.
- Each failure is classified (`harness` / `guardrail_block` / `test-plan` /
  `server-error` / `unclassified`) — the runner never declares "product" itself.

**Key functions:** `run_execution(plan, *, backend, sandbox, max_steps, allowed_domains)`.

## Phase 5 — Verify  (`bot/verify/`)

**Input:** `qa-execution-v1` + plan. **Output:** `qa-verification-v1`.

Pipeline per candidate, fully isolated:
1. **Gate** (`evaluate_gate`): non-product `failure_class` or missing evidence →
   `DISMISSED` immediately; only evidence-backed candidates proceed.
2. **Replay** (`replay_candidate`): re-run in a fresh session; `reproduced=True` only
   if the terminal assertion fails again. Unknown actions raise.
3. **Judge** (`judge`): default is deterministic (verified iff reproduced + product-
   eligible); a custom LLM judge plugs into `run_verification(judge=...)`. A judge
   exception dismisses that one candidate and never loses the run.

**Key functions:** `run_verification(execution, plan, *, judge, page_dir)`.

## Phase 6 — Report  (`bot/report/`)

**Input:** `qa-verification-v1` + plan. **Output:** `qa-report-v1` + repro specs.

- `dedupe_verified_findings`: exact normalized key
  (`title | url | target_ref | step_index | failure_class`); highest confidence wins;
  every merge is recorded in a ledger (nothing silently vanishes).
- Defects sorted by severity (`P0 → P3`).
- `repro.build_repro_spec` emits a runnable Playwright `.spec.ts`; URL matchers are
  always RegExp literals (never a bare path string that fails to parse).

**Key functions:** `run_report(verification, plan, *, page_dir)`.

## Contracts (frozen, `bot/contracts/`)

| File | Produced by | Purpose |
|---|---|---|
| `planner-input-v1.json` | Crawl | Page inventory: components, boxes, viewport |
| `qa-plan-v1.json` | Plan | Single-page test plan |
| `qa-plan-v2.json` | Plan | Multi-page journey plan (+ `page_registry`) |
| `qa-execution-v1.json` | Execute | Per-step results + candidate findings |
| `qa-verification-v1.json` | Verify | Verified / dismissed findings + verdicts |
| `qa-report-v1.json` | Report | Deduped defects + repro index |

These are frozen copies (see `PROVENANCE.md`). A breaking change introduces a **new
versioned file** plus an explicit migration — never an in-place redefinition of v1.
