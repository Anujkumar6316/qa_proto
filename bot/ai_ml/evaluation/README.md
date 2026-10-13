# AI task evaluation

Evaluation measures the effect of model, provider, prompt, parser, and validation changes on fixed inputs. It is distinct from browser-backend parity testing.

- Store sanitized and reviewed cases under `datasets/<task>/`.
- Use `runners/` for deterministic execution and baseline comparison.
- Put metric definitions and calculations in `metrics/`.
- Keep generated reports in `reports/`; do not treat candidate output as approved ground truth.
- Always compare candidate vs. baseline on the same case IDs. Report counts, rates, error classes, and case-level regressions.

The repository may already have an evaluation harness. Reuse it rather than creating a competing runner; the files shown here are target responsibilities, not a requirement to duplicate existing code.
