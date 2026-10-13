# Configuration ownership

Keep non-secret defaults and model/task settings here. Use the project's existing settings loader if one exists; do not introduce a second configuration framework just for this folder.

- `model_profiles.example.yaml` documents provider configuration using environment-variable *names* only.
- `task_defaults.yaml` holds per-task parameters such as temperature, output-token limit, timeout, and retry budget.
- Secret values belong in the existing secret manager or environment and must never be committed or written to logs.
- Avoid defining the same setting both in code and YAML. Document precedence if environment overrides are supported.
