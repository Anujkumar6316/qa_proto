# Shared AI utilities

Place only helpers shared by at least two AI tasks here, such as normalized AI-layer exceptions, common telemetry fields, and bounded retry policy. Task-specific rules belong in the task directory; provider transport belongs in `providers/`; browser retry and failure classification belong to the existing runtime.

Before adding a utility, search for an existing equivalent in the repository. Avoid a generic `utils.py` dumping ground.
