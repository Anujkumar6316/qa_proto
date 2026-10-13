# Prompt library — one prompt per named file

Canonical source of every model prompt in QA Bot v0.2. No prompt text lives in
Python — tasks load these files via `bot.ai_ml.prompts.loader`.

Frozen at v0.2.0, ported byte-identical from the reviewed sources (provenance below).
Per `AGENTS.md`: do not silently change a released prompt. Behavior-changing edits
create a new version file + golden eval, never an in-place rewrite.

## Layout

```
prompts/
  planner/
    system.md                     # runtime planner system prompt
    user_template.md              # runtime user template (strategy-guide + planner_input)
    strategies/
      comprehensive.md            # 5-dimension enterprise suite
      journey.md                  # multi-page checkout/booking/auth (qa-plan-v2)
      negative_edge.md            # validation + boundary
      positive_flow.md            # primary conversions
      security_injection.md       # XSS/sanitization probes
      strict_adversarial.md       # risk-weighted adversarial matrix
  judge/
    system.md                     # adversarial verifier (false-positive killer)
    user_template.md              # candidate + evidence + replay context
  teacher/
    system.md                     # Principal QA Architect (dataset generation)
    user_template.md              # scenario + planner_input
    scenarios/
      smoke.md
      negative_edge.md
      dynamic_ui.md
      security_validation.md
  loader.py                       # load_prompt / load_strategy / load_scenario
  manifest.yaml                   # inventory + contract + provenance
```

## Provenance (frozen 2026-10-13, byte-identical)

| Prompt | Source |
|---|---|
| planner/system.md | core/pipeline/plan/prompts.py `SYSTEM_PROMPT` |
| planner/user_template.md | core/pipeline/plan/prompts.py `format_user_prompt` |
| planner/strategies/*.md | core/pipeline/plan/strategy_prompts/*.md (verbatim copies) |
| judge/system.md | core/pipeline/verify/judge.py `VERIFIER_SYSTEM_PROMPT` |
| judge/user_template.md | core/pipeline/verify/judge.py `evaluate()` user_content |
| teacher/system.md | planner/yukti_dataset/prompts.py `SYSTEM_PROMPT` |
| teacher/scenarios/*.md | planner/yukti_dataset/prompts.py `SCENARIO_INSTRUCTIONS` |
| teacher/user_template.md | planner/yukti_dataset/prompts.py `build_teacher_prompt` |
