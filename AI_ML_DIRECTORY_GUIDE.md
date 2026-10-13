# AI/ML Directory Structure and Maintenance Guide

> **Interpretation:** This guide targets the browser-based QA automation project described in `PLAYWRIGHT_MIGRATION_PLAN.md`. It separates model reasoning from the browser harness. It is a proposed structure, not a claim that the current repository already has these modules.

## 1. Design rule

The AI/ML layer should own **model interaction and model-output quality**. The existing application/runtime should own **browser interaction and deterministic policy enforcement**.

- AI/ML: provider adapters, task-specific prompts, structured-output parsing, semantic validation, model-task configuration, evaluation datasets, and model-quality metrics.
- Existing runtime (`core/`, `api/`, or whatever paths the repository currently uses): browser lifecycle, Playwright/agent-browser drivers, locator resolution, waits/timeouts, action execution, telemetry collection, replay, artifact persistence, run budgets, and enforcing whether a run may continue.
- Shared contracts: keep the existing `planner-input-v1`, `qa-execution-v1`, `qa-verification-v1`, and other current contracts in their **current source-of-truth location** during the migration. Do not silently duplicate or move them into `ai_ml/`.

**Migration guardrail:** the Playwright migration plan explicitly keeps planner and judge behavior unchanged during the browser-backend swap. Introducing this directory structure must not change prompts, model settings, planner logic, judge logic, or test orchestration as part of that migration.

## 2. Proposed repository layout

Add `bot/ai_ml/` as the model-layer subpackage inside the `bot` package. Do not reorganize the runtime directories just to match this example.

```text
repo-root/
├── bot/
│   ├── ai_ml/
│   ├── README.md                       # Entry point: purpose, boundaries, how to run checks
│   ├── ARCHITECTURE.md                 # Dependency rules and model-task data flow
│   ├── AGENTS.md                       # Binding maintenance instructions for coding agents
│   ├── config/
│   │   ├── README.md                   # Configuration rules and environment variables
│   │   ├── model_profiles.example.yaml # Safe, non-secret model/provider examples
│   │   └── task_defaults.yaml          # Per-task decoding/time-budget defaults
│   ├── providers/
│   │   ├── README.md                   # Provider adapter contract
│   │   ├── protocol.py                 # Small interface every provider implements
│   │   ├── factory.py                  # Select configured provider; no task logic
│   │   ├── openai_compatible.py        # Adapter for OpenAI-compatible endpoints
│   │   └── mock.py                     # Deterministic provider for tests
│   ├── tasks/
│   │   ├── README.md                   # Inventory of AI tasks and their input/output contracts
│   │   ├── planner/
│   │   │   ├── README.md               # Planner-specific purpose and contract
│   │   │   ├── service.py              # One public entry point to request a plan
│   │   │   ├── parser.py               # Convert raw model response to structured output
│   │   │   ├── validation.py            # Deterministic plan and contract checks
│   │   │   └── prompts/
│   │   │       └── v1/
│   │   │           ├── system.md        # Versioned system instructions
│   │   │           ├── user_template.md # Versioned prompt template and placeholders
│   │   │           └── manifest.yaml     # Prompt version, variables, output contract, notes
│   │   ├── verification/
│   │   │   ├── README.md               # Phase 2 verification/preflight verdict task
│   │   │   ├── service.py
│   │   │   ├── parser.py
│   │   │   ├── validation.py
│   │   │   └── prompts/v1/              # Same files as planner, owned by this task
│   │   └── judge/
│   │       ├── README.md               # Evidence-based finding/replay judge task
│   │       ├── service.py
│   │       ├── parser.py
│   │       ├── validation.py
│   │       └── prompts/v1/              # Same files as planner, owned by this task
│   ├── common/
│   │   ├── README.md                   # Rules for genuinely cross-task utilities
│   │   ├── errors.py                   # Shared AI-layer exceptions
│   │   ├── telemetry.py                # Model/task latency and outcome fields
│   │   └── retry_policy.py              # Bounded retries for explicitly retryable failures
│   └── evaluation/
│       ├── README.md                   # How to run and interpret model evaluations
│       ├── datasets/
│       │   ├── README.md               # Dataset format, provenance, privacy, versioning
│       │   ├── planner/                # Golden planner inputs and expected properties
│       │   ├── verification/           # Golden verification cases and expected labels
│       │   └── judge/                  # Golden judge cases and expected labels
│       ├── runners/
│       │   ├── README.md               # Evaluation entry points and reproducibility rules
│       │   ├── run_eval.py              # Runs a named evaluation suite
│       │   └── compare_baseline.py      # Compares current output with a frozen baseline
│       ├── metrics/
│       │   ├── README.md               # Metric definitions; do not hide regressions in averages
│       │   ├── planner_metrics.py       # Plan validity/coverage metrics
│       │   ├── verification_metrics.py  # Verdict precision/recall and false-block metrics
│       │   └── judge_metrics.py         # Finding precision/recall and agreement metrics
│       ├── baselines/                  # Small, versioned, reviewed baseline manifests/results
│       └── reports/                    # Generated reports; usually git-ignored
├── core/                               # Existing deterministic runtime/browser modules: keep in place
├── api/                                # Existing API layer: keep in place
├── tests/                              # Prefer existing repository-wide test convention
└── ...                                 # Existing files, architecture docs, reports, etc.
```

The files marked above are **target responsibilities**. If a file already exists elsewhere, keep its current implementation until callers and imports have been deliberately migrated. Do not create two competing implementations just to populate this tree.

## 3. Why each boundary exists

| Location | Put here | Do not put here |
|---|---|---|
| `config/` | Model names, endpoint environment-variable names, token limits, temperatures, task timeouts, feature flags | API keys, passwords, per-request business logic, prompts duplicated as YAML strings |
| `providers/` | Transport/API calls, provider-specific request/response mapping, provider error normalization | Planner rules, judge decisions, prompt text, browser operations, application-specific verdict policy |
| `tasks/planner/` | Planner prompt, task-specific parsing, validation, service entry point | Playwright calls, element clicks, locator retries, execution lifecycle |
| `tasks/verification/` | Phase 2 verification prompt and interpretation of the model's structured verdict | The control-flow decision that allows a run to proceed; the runtime must enforce the gate deterministically |
| `tasks/judge/` | Evidence-based judge prompt, response parsing and judge-specific quality checks | Replaying a browser case, selecting replay timing, swallowing harness errors, or converting every failure into an app defect |
| `common/` | Small utilities used by at least two AI tasks | A miscellaneous dumping ground, task-specific policy, generic helpers used only once |
| `evaluation/datasets/` | Sanitized, deterministic test cases and expected outcomes | Secrets, live user data, generated results presented as ground truth without review |
| `evaluation/runners/` | Repeatable dataset execution and comparison with a baseline | Production orchestration or browser action execution |
| `evaluation/metrics/` | Clearly defined model-quality metrics and breakdowns | Model calls, prompt templates, or thresholds that silently alter runtime behavior |
| `evaluation/reports/` | Generated local/CI reports | Source code or hand-edited golden truth |

### Important: task code vs. runtime enforcement

The model can return a verdict such as `INVALID`; the runtime must be responsible for **stopping the run**. The model can propose a plan; the runtime validates the plan before execution. The judge can recommend that a candidate finding is real; the replay/runtime logic determines whether the required deterministic reproductions occurred. A prompt is not a security boundary or a control-flow guarantee.

## 4. Task lifecycle

For every AI task, keep the flow recognizable and in this order:

1. `service.py` receives the typed/contracted task input.
2. The task loads its **explicitly versioned** prompt and task configuration.
3. The provider adapter sends the request and returns a raw response plus usage/latency metadata.
4. `parser.py` parses the response without executing model-generated code.
5. `validation.py` validates fields and task-specific invariants against the existing shared contracts.
6. `service.py` returns a typed result or a classified AI-layer error.
7. The caller/runtime applies deterministic policy and decides the next action.
8. Evaluation/telemetry records task version, provider/model identifier, prompt version, elapsed time, parse/validation outcome, retry count, and relevant token usage when available.

Never let malformed model output bypass validation. Never use `eval()` to parse model output. If output repair is supported, it must be explicitly bounded, observable, separately counted, and covered by evaluation tests.

## 5. Prompt versioning rules

- Prompt text lives beside the task that owns it, not in a global unstructured `prompts/` bucket.
- A released prompt version is immutable. To change task behavior, create `v2/` or follow the repository's explicitly documented versioning convention; do not silently rewrite `v1/`.
- `manifest.yaml` should document: `task`, `prompt_version`, `input_contract`, `output_contract`, required template variables, model assumptions, and a short change note.
- All placeholders must be listed in the manifest and validated before the model call.
- Do not put model secrets or personal/customer data in prompts checked into source control.
- Keep prompts deterministic where possible. Temperature and other decoding changes must be evaluated just like prompt changes.
- Prompt changes require a before/after golden evaluation and a brief recorded rationale.

## 6. Provider rules

- Task modules call the provider interface, never a vendor SDK directly.
- Provider adapters perform transport and normalize API failures. They do not decide if a plan or finding is correct.
- Use the mock provider for unit and contract tests. Unit tests should not need a network or a real model.
- Configure secrets through the existing secret manager/environment. Commit only `.example` configuration with variable names, never secret values.
- Retries must be bounded and limited to explicitly retryable transport/rate-limit failures. Do not automatically retry semantic disagreements or assertion failures as though they were network errors.
- A provider/model change is a benchmark change: run the same golden suite and save the comparison.

## 7. Evaluation rules

Each task needs a small, versioned golden dataset before it is considered production-ready.

- **Planner:** schema/contract pass rate, invalid-plan rate, required-action/step coverage, and per-site or per-feature breakdowns. Do not use only a single aggregate score.
- **Verification:** precision/recall for verdict labels, false-valid and false-invalid counts, and performance on challenge/blocked pages. False acceptance and false blocking must be reported separately.
- **Judge:** precision/recall for candidate findings, agreement with reviewed labels, and a breakdown by failure class. Harness/environment errors must not be scored as application defects.
- Compare baseline vs. candidate on the **same inputs**. Report counts as well as rates, and identify regressions by case ID.
- Keep golden labels reviewed and stable. Keep generated run outputs in `reports/`; do not automatically overwrite the goldens with new model output.
- Browser-backend parity testing remains separate from AI evaluation. During the agent-browser → Playwright migration, freeze planner/judge behavior and compare backend verdicts as specified in the migration plan.

## 8. Shared contracts and compatibility

The migration plan names existing contracts including `planner-input-v1`, `qa-execution-v1`, and `qa-verification-v1`. Before changing code, locate the actual definitions and all call sites.

- Keep the current contract source of truth where it is today during the browser-driver migration.
- Do not copy a JSON schema or Pydantic model into `ai_ml/` just to make imports convenient.
- Add fields only when the contract's compatibility policy allows additive fields. Preserve existing field names and meanings.
- If a contract truly needs a breaking change, introduce a new version and an explicit migration; don't silently redefine `v1`.
- AI task internal structures can exist inside each task, but conversion to/from shared artifact contracts must occur in one clearly named mapping/validation boundary.

## 9. Maintenance instructions for coding models

1. Read `bot/ai_ml/AGENTS.md`, `bot/ai_ml/ARCHITECTURE.md`, this guide, and the relevant task README before making changes.
2. Search the repository for existing implementations and imports before adding or moving files. Preserve current public function signatures unless the task explicitly requires a change.
3. Make the smallest change that solves the requested task. Do not refactor unrelated planner, judge, browser, API, and evaluation code in one patch.
4. Add a new top-level directory only when there is a distinct responsibility, at least two concrete files/use cases, and a README describing ownership.
5. Put logic in the narrowest owner: provider transport in `providers/`, model-task behavior in `tasks/<task>/`, shared AI infrastructure in `common/`, measurement in `evaluation/`, browser/runtime control in the existing runtime package.
6. Do not create duplicate classes, prompts, configs, or schemas. If a suitable owner exists, extend it.
7. Update the owning README and relevant tests whenever a new module or responsibility is added or removed.
8. Run focused unit/contract tests first, then the relevant golden evaluation, then the broader test suite when practical. Report commands actually run and failures honestly.
9. Never delete old behavior or adapters until the relevant migration exit criteria are met.
10. If the repository's existing layout conflicts with this proposed tree, document the difference and follow the current source of truth until an explicit migration is approved. This document is a boundary guide, not permission for a sweeping file move.

## 10. Recommended implementation order

1. Inventory current planner, verification, judge, and provider call sites; identify schemas and current tests.
2. Add these documentation files and agree on the dependency boundary first.
3. Introduce the provider interface as a thin seam around existing calls, without changing behavior.
4. Add mock-provider unit/contract tests around the current behavior.
5. Move or wrap one task at a time, starting with the smallest task; preserve prompt content and model settings byte-for-byte where feasible.
6. Add golden datasets and a baseline report before tuning prompts or models.
7. Only after parity is established should prompt/model changes be proposed independently from the Playwright backend migration.

## 11. Keep out of scope unless the product actually needs it

Do not add model training pipelines, fine-tuning jobs, feature stores, vector databases, embedding jobs, agent frameworks, multi-agent orchestration, or GPU-serving infrastructure simply because this directory is called `ai_ml`. This project layout is for the model tasks evidenced by the current QA automation design. Add those capabilities only when there is a concrete requirement and an owner for each one.
