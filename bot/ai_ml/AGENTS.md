# AI/ML Coding-Agent Rules

These rules are mandatory for automated coding agents modifying this package.

1. Before editing, read `README.md`, `ARCHITECTURE.md`, this file, and the owner README for the target task.
2. Search for existing implementations, imports, prompt text, schemas, and tests before creating or moving anything.
3. Do not move existing modules solely to fit the proposed tree. Keep current public interfaces stable unless the issue explicitly requires a change.
4. Keep provider transport in `providers/`; task behavior and prompts in `tasks/<task>/`; cross-task AI infrastructure in `common/`; metrics and golden cases in `evaluation/`.
5. Do not put Playwright, browser-driver lifecycle, locator resolution, browser actions, waits, replay, or run-control policy in this package.
6. Do not duplicate `planner-input-v1`, `qa-execution-v1`, `qa-verification-v1`, or other shared contracts. Locate and import the existing source of truth.
7. Never let an LLM response directly execute an action or bypass deterministic validation. Never parse model output with `eval()`.
8. Version prompts explicitly. Do not silently change a released prompt version; create a new version and evaluate it.
9. Use the mock provider for unit tests. Tests must not require a network or paid model call unless explicitly marked as integration tests.
10. Retries must be bounded and only used for documented retryable failures. Never retry assertion failures or semantic disagreements as transport errors.
11. Every behavior-changing prompt/model change must run the task's golden evaluation against a recorded baseline and report case-level regressions.
12. Do not turn `harness_error`, `env_error`, `blocked_bot`, `guardrail_block`, or `timeout` into an app defect merely because an LLM says so. Respect the runtime's failure-classification contract.
13. During the agent-browser to Playwright migration, do not change planner or judge behavior in the same change. Keep the browser backend swap and model-quality tuning separate.
14. Update the owning README, tests, and evaluation metadata when responsibilities or contracts change.
15. If the repository layout conflicts with this scaffold, follow the repository's existing source of truth and document the discrepancy. Do not perform a broad directory rewrite without an explicit task.
