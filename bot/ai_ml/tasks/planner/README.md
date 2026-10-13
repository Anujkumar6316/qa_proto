# Planner task

**Purpose:** produce a candidate QA plan from the existing planner input artifact.

**Owns:** planner task service, prompt versions, parsing, plan-specific semantic validation, and planner evaluation cases/metrics.

**Does not own:** crawling, browser snapshots, component registry persistence, `BrowserDriver`, Playwright calls, executing actions, replay, or global run-control decisions.

**Compatibility:** preserve the existing planner input/output contract and public caller behavior. During the Playwright migration, do not tune prompt wording, model settings, or planning logic in the same change. If the plan's shared schema is already defined elsewhere, import it rather than copying it here.
