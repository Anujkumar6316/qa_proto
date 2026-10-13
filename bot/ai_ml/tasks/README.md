# Model tasks

Each subdirectory is one business capability with one public service entry point, its own prompt versions, parsing, validation, and task README.

A task must:
1. Define its input and output using existing shared contracts where applicable.
2. Keep provider-specific details out of task code.
3. Parse model output as untrusted data and validate before returning.
4. Expose a stable service function to the runtime.
5. Have golden evaluation cases and metrics before behavior is tuned.

Do not introduce a new task directory for a helper function; place it with the task that owns the behavior or in `common/` only if it is genuinely shared.
