# API Reference — `/api/v2`

FastAPI app: `bot.interfaces.api:app`. Start it with:

```bash
uv run poe api          # http://127.0.0.1:8000
uv run poe serve        # API (:8000) + Studio (:7860) together
```

Interactive docs: **http://127.0.0.1:8000/api/v2/docs** · OpenAPI: `/api/v2/openapi.json`.

All endpoints are synchronous `def` (FastAPI runs them in a threadpool) because the
services call `asyncio.run()` internally. Every artifact reference returned is
**run-relative** — absolute host paths never appear in responses.

## Conventions

- Base prefix: `/api/v2`
- A **slug** identifies a crawl (e.g. `example_com__login`); it is the directory name
  under the artifacts root and the key used by every phase endpoint.
- Errors use HTTP status: `404` unknown slug · `409` prerequisite missing (no plan yet)
  · `422` validation (bad URL, grounding rejection) · `400` path-escape attempt.

## Endpoints

### Health

```bash
curl -s localhost:8000/api/v2/live            # {"status":"live"}  (no probe, cheap)
curl -s localhost:8000/api/v2/health          # version + phases + artifacts dir
```

### Crawl

```bash
# Crawl a URL (fake backend = offline). Returns {slug, run_id, manifest}.
curl -s -X POST localhost:8000/api/v2/crawl \
  -H 'content-type: application/json' \
  -d '{"url":"https://example.com/login","backend":"fake","scope":"all"}'
```

Request body (`CrawlRequest`):

| Field | Type | Default | Notes |
|---|---|---|---|
| `url` | string | — | Absolute `http(s)` URL |
| `backend` | string | `fake` | `fake` \| `playwright` |
| `scope` | string | `all` | `all` \| `forms` \| `catalog` \| `navigation` |
| `objective` | string | `""` | Free-text planning objective |
| `allow_private` | bool | `false` | Allow loopback/private hosts (dev only) |

```bash
# List indexed crawls
curl -s localhost:8000/api/v2/crawls
```

### Ground

```bash
curl -s -X POST localhost:8000/api/v2/ground/example_com__login
# -> {slug, total, ok_count, by_type, issues, audit}
```

### Plan

```bash
curl -s -X POST localhost:8000/api/v2/plan/example_com__login
# -> {slug, plan, plan_ref}
```

### Execute / Verify / Report

```bash
# Execute the plan (fake backend). Requires a plan (run /plan first).
curl -s -X POST "localhost:8000/api/v2/execute/example_com__login?sandbox=false"

# Verify (execute -> verify). Returns qa-verification-v1.
curl -s -X POST localhost:8000/api/v2/verify/example_com__login

# Report (execute -> verify -> report). Returns qa-report-v1 + repro_specs.
curl -s -X POST localhost:8000/api/v2/report/example_com__login
```

`/execute` accepts a `?sandbox=true` query param to unlock destructive-action flows.

### Artifacts

```bash
# Manifest + page-dir ref for a crawl
curl -s localhost:8000/api/v2/artifacts/example_com__login

# Serve a run-relative artifact (containment-checked; traversal -> 400/404)
curl -s localhost:8000/api/v2/artifacts/example_com__login/file/shared/planner_input.json
```

## End-to-end (copy/paste)

```bash
API=localhost:8000
SLUG=$(curl -s -X POST $API/api/v2/crawl \
  -H 'content-type: application/json' \
  -d '{"url":"https://example.com/login","backend":"fake"}' | python3 -c 'import sys,json;print(json.load(sys.stdin)["slug"])')
curl -s -X POST $API/api/v2/ground/$SLUG
curl -s -X POST $API/api/v2/plan/$SLUG
curl -s -X POST $API/api/v2/report/$SLUG | python3 -m json.tool
```

## Extending

Add a route inside `create_app()`. Keep handlers thin: call a `bot` service, map the
result to a dict, and return run-relative refs via `bot.ids.relative_ref`. Raise
`HTTPException` for boundary errors; never let a raw traceback or absolute path escape.
