# Evaluation runners

A runner loads a named fixed dataset, invokes the public task service, validates outputs, and writes a machine-readable result including case ID, model/provider ID, prompt version, latency, parse/validation status, and outcome. Baseline comparison must show per-case diffs as well as aggregate metrics.

Reuse the current harness if one exists. Do not wire browser execution into these runners unless a separate integration suite explicitly requires it.
