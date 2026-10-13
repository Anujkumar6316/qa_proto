# AI/ML layer

This package owns model calls, task prompts, structured-output parsing/validation, and AI-task evaluation. It does not own browser sessions, Playwright, locators, waits, execution/replay, API routing, or final run-control policy.

## Start here

1. Read [`AGENTS.md`](AGENTS.md) before using a coding agent to change this package.
2. Read [`ARCHITECTURE.md`](ARCHITECTURE.md) for dependency direction and flow.
3. Read the README for the task you intend to change under `tasks/`.
4. Use `evaluation/` to measure behavior before changing prompts or models.

This is a starter scaffold, not a migrated implementation. Connect it to existing modules gradually, without duplicating existing contracts or changing behavior during the browser-driver migration.
