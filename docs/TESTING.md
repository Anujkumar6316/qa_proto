# Testing

The suite is **deterministic and offline** — no network, no real browser, no paid model.
The `fake` driver and `mock` provider stand in for the real ones, and a test asserts the
API end-to-end via FastAPI's `TestClient`.

## Run

```bash
uv run poe test         # or: pytest
uv run poe test-v       # verbose
pytest tests/test_api.py -v
```

Config lives in `pyproject.toml` (`[tool.pytest.ini_options]`): `pythonpath=["."]`,
`testpaths=["tests"]`.

## Layout

```
tests/
  conftest.py            # puts QA_v0.2 on sys.path
  test_ingest.py         # upload boundary: spaces, traversal, abs-path hints, SSRF
  test_ground.py         # contract + box/refs/folds/files audit
  test_grounding.py      # anti-hallucination gate (hallucinated refs, cardinality, …)
  test_plan.py           # mock provider + fail-closed gate
  test_crawl.py          # normalizer role mapping + crawl contract
  test_guardrails.py     # destructive keywords, external nav, step budget
  test_execute.py        # pass/fail/blocked/budget, per-case session close
  test_verify_report.py  # gate/replay/judge isolation, dedupe, repro parsing
  test_pipeline.py       # full six-phase chain + a real-defect path
  test_prompts.py        # every prompt loads; strategies match legacy byte-for-byte
  test_api.py            # FastAPI app over the services (TestClient)
```

## What's covered

- **Boundaries.** `test_ingest` proves the `Book 12.xlsx` class is fixed: a filename
  with spaces ingests cleanly; `../../etc/passwd` and absolute `/home/...` hints are
  treated as names only; oversize/empty uploads are rejected; SSRF blocks private hosts.
- **Fail-closed.** Empty components raise; hallucinated `@eN` refs are rejected; unknown
  actions raise; the sandbox gate blocks destructive flows unless opened.
- **Isolation.** The prompt tests assert each strategy equals its frozen legacy source,
  so drift is caught. A repo-wide `grep` confirms zero legacy imports.
- **Composition.** `test_pipeline` runs crawl → ground → plan → execute → verify → report
  in one shot and checks the event order, then repeats with a deliberately failing plan
  to confirm a `VERIFIED` defect + runnable repro is produced.

## Adding tests

- Mirror the source layout (`tests/test_<area>.py`).
- Use `tmp_path` for any filesystem work; never write to the real artifacts root.
- Prefer the `fake` backend and `mock` provider. Mark anything needing a real browser or
  network explicitly (and keep it out of the default run).
- For API changes, extend `tests/test_api.py` with the `TestClient` fixture, which
  already redirects the artifact root to a temp dir.
