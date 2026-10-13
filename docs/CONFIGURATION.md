# Configuration

All settings live in one `Settings` class (`bot/settings.py`) built on
`pydantic-settings`. Every variable is namespaced **`QA_BOT_`** and can be set via
environment variable or a `.env` file (copy `.env.example`).

```bash
cp .env.example .env
```

Precedence: explicit environment variable > `.env` > default.

## Storage

| Variable | Default | Notes |
|---|---|---|
| `QA_BOT_ARTIFACTS_DIR` | `artifacts` | Relative paths anchor to the **package root** (`QA_v0.2/`), not the CWD. Set an absolute path to override. |

## App

| Variable | Default | Notes |
|---|---|---|
| `QA_BOT_PROJECT_NAME` | `QA Bot v0.2` | Display name |
| `QA_BOT_VERSION` | `0.2.0` | Reported by banner/API |
| `QA_BOT_API_V2_PREFIX` | `/api/v2` | API route prefix |
| `QA_BOT_DEBUG` | `false` | Debug flag |
| `QA_BOT_LOG_LEVEL` | `INFO` | Logging level |

## Browser budgets

| Variable | Default | Notes |
|---|---|---|
| `QA_BOT_ACTION_TIMEOUT_MS` | `5000` | Per-action timeout |
| `QA_BOT_NAV_TIMEOUT_MS` | `30000` | Navigation timeout |
| `QA_BOT_CASE_BUDGET_S` | `60` | Per-test-case wall budget |
| `QA_BOT_RUN_BUDGET_S` | `600` | Per-run wall budget |
| `QA_BOT_SESSION_GATE_ATTEMPTS` | `3` | Session-readiness retries |
| `QA_BOT_SESSION_GATE_TIMEOUT_MS` | `30000` | Readiness probe budget |

### Tunnel profile (slow ephemeral dev links)

| Variable | Default |
|---|---|
| `QA_BOT_TUNNEL_ACTION_TIMEOUT_MS` | `10000` |
| `QA_BOT_TUNNEL_NAV_TIMEOUT_MS` | `60000` |
| `QA_BOT_TUNNEL_SESSION_GATE_TIMEOUT_MS` | `60000` |
| `QA_BOT_TUNNEL_CASE_BUDGET_S` | `120` |

## Step budgets

| Variable | Default | Notes |
|---|---|---|
| `QA_BOT_MAX_STEPS_SINGLE` | `6` | Max steps per single-page test case |
| `QA_BOT_MAX_STEPS_JOURNEY` | `12` | Max steps per journey test case |

## Sandbox & SSRF gates (fail-closed)

| Variable | Default | Notes |
|---|---|---|
| `QA_BOT_SANDBOX_OPEN_GATE` | `false` | `true` permits destructive actions on any site |
| `QA_BOT_SANDBOX_ALLOWED_DOMAINS` | `""` | Comma list; `*` = wildcard |
| `QA_BOT_ALLOW_PRIVATE_HOSTS` | `false` | `true` allows loopback/private hosts (local dev) |

## Planner / LLM

| Variable | Default | Notes |
|---|---|---|
| `QA_BOT_PLANNER_PROVIDER` | `mock` | `mock` is free/offline; set a real provider when ready |
| `QA_BOT_PLANNER_MODEL` | `mock` | Model id for the provider |
| `QA_BOT_LLM_BASE_URL` | `""` | OpenAI-compatible base URL |
| `QA_BOT_LLM_API_KEY` | `""` | API key (never commit; env/secret store only) |
| `QA_BOT_LLM_TIMEOUT_S` | `30` | LLM request timeout |
| `QA_BOT_LLM_MAX_RETRIES` | `1` | Bounded retries for transport errors only |

## Uploads

| Variable | Default | Notes |
|---|---|---|
| `QA_BOT_MAX_UPLOAD_BYTES` | `10485760` | Upload size cap (10 MB) |

## Reading settings in code

```python
from bot.settings import get_settings

settings = get_settings()                 # cached singleton
root = settings.resolved_artifacts_dir()  # absolute, created, CWD-independent
```
