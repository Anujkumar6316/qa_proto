# Prompt Library

Every model prompt lives in its own file under `bot/ai_ml/prompts/`. No prompt text is
inlined in Python — tasks load files via `bot.ai_ml.prompts.loader`.

## Layout

```
bot/ai_ml/prompts/
  loader.py          # load_prompt / load_strategy / load_scenario (traversal-safe)
  manifest.yaml      # inventory: task, role, contract, variables, provenance
  planner/
    system.md
    user_template.md
    strategies/  comprehensive  journey  negative_edge  positive_flow
                 security_injection  strict_adversarial
  judge/
    system.md        # adversarial verifier (false-positive killer)
    user_template.md
  teacher/
    system.md        # Principal QA Architect (dataset generation)
    user_template.md
    scenarios/  smoke  negative_edge  dynamic_ui  security_validation
```

## Loading

```python
from bot.ai_ml.prompts import load_prompt, load_strategy, load_scenario

system   = load_prompt("planner/system.md")
strategy = load_strategy("comprehensive")     # planner/strategies/comprehensive.md
scenario = load_scenario("smoke")             # teacher/scenarios/smoke.md
```

- Paths are relative to `bot/ai_ml/prompts/`; traversal (`../`) raises.
- Missing files raise `FileNotFoundError`.
- Results are cached (`lru_cache`); prompts are immutable at runtime.

## Strategies (planner)

| Strategy | Intent |
|---|---|
| `comprehensive` | Balanced 5-dimension enterprise suite |
| `journey` | Multi-page flows (checkout/booking/auth) → `qa-plan-v2` |
| `negative_edge` | Validation + boundary limits |
| `positive_flow` | Primary conversions |
| `security_injection` | XSS / sanitization probes |
| `strict_adversarial` | Risk-weighted adversarial matrix |

## Scenarios (teacher / dataset generation)

| Scenario | Intent |
|---|---|
| `smoke` | Core workflows & primary conversions |
| `negative_edge` | Validation, boundary, error recovery |
| `dynamic_ui` | Disclosures, modals, tabs |
| `security_validation` | XSS sanitization, disabled gating, auth |

## Provenance & change policy

Frozen at v0.2.0, ported **byte-identical** from the reviewed legacy sources
(`core/pipeline/plan/prompts.py`, `core/pipeline/plan/strategy_prompts/*.md`,
`core/pipeline/verify/judge.py`, `planner/yukti_dataset/prompts.py`). See
`prompts/README.md` for the source table.

Per the model-layer rules: **do not silently change a released prompt.** A
behavior-changing edit adds a new versioned file and is measured against a golden
evaluation before release — never an in-place rewrite of a frozen prompt.

## Templates

`user_template.md` files contain `{placeholders}` filled by the calling task (e.g.
`{strategy}`, `{planner_input}`, `{plan_version}`). The manifest lists each template's
required variables so a task can validate them before rendering.
