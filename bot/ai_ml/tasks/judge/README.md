# Judge task

**Purpose:** judge a candidate application finding from the evidence supplied by the existing verification/replay pipeline.

**Owns:** judge prompt versions, response parser, judge-specific validation, and reviewed gold cases/metrics.

**Does not own:** performing browser replay, deciding whether replay is reproducible, classifying browser/infra/network failures at the driver boundary, or turning every non-pass result into an application defect.

Respect the existing rule that harness and environment failures are not candidate application findings. During the Playwright backend migration, keep judge behavior fixed and evaluate it separately later.
