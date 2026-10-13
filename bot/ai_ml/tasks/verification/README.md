# Verification task

**Purpose:** return the existing structured Phase 2/preflight verification verdict.

**Owns:** verification prompt versions, parser, output validation, and false-valid/false-invalid evaluation cases.

**Does not own:** the control-flow gate itself. The runtime must stop the run when the contract says the result is `INVALID`; a prompt alone cannot enforce this.

Keep challenge detection and authorization boundaries explicit. This task must not implement stealth, fingerprint spoofing, CAPTCHA solving, or challenge evasion.
