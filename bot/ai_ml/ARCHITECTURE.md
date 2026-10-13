# AI/ML Architecture and Boundaries

## Dependency direction

```text
Existing pipeline/runtime (bot.crawl / bot.execute / bot.verify / ...)
    ├── may call ──> bot.ai_ml.tasks.planner
    ├── may call ──> bot.ai_ml.tasks.verification
    └── may call ──> bot.ai_ml.tasks.judge
                         │
                         ├── task prompt + task validation
                         ├── bot.ai_ml.providers interface
                         └── bot.ai_ml.common (small shared utilities)

bot.ai_ml.evaluation ──> task entry points + fixed/sanitized test datasets

AI/ML tasks must not import the browser driver, Playwright, FastAPI routes,
or run orchestration. Avoid circular dependencies.
```

## Responsibilities

- **Planner:** turns the existing planner input artifact into a candidate plan. It does not execute steps.
- **Verification:** returns a structured Phase 2 verdict. The runtime—not the prompt—must enforce that an `INVALID` result halts the run.
- **Judge:** evaluates evidence using the existing judge contract. Replay and reproduction rules remain in the runtime; only eligible, reproducible candidates should reach the judge.
- **Provider:** performs model transport and normalizes provider errors/usage metadata. It does not know task policy.
- **Evaluation:** measures model task outputs on fixed inputs; it does not control production runs.
- **Runtime:** remains the owner of browser lifecycle, locator resolution, action policies, timeouts, retries for browser errors, replay, artifact persistence, and run budgets.

## Standard model-task flow

`task input → prompt version + task config → provider → raw response → parser → deterministic validation → typed result/error → runtime policy`

An LLM output is untrusted input. It must be parsed, validated, and checked before use. Model confidence values do not override deterministic guardrails or artifact contracts.

## Shared artifact contracts

Use the repository's current contract source of truth. The Playwright migration plan names `planner-input-v1`, `qa-execution-v1`, and `qa-verification-v1`; locate their actual definitions before editing. Do not create duplicate schemas in this package.
