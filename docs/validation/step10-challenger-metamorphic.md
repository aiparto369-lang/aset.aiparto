# Step 10 — Challenger + Metamorphic Validation

This step adds a non-human challenger classifier and metamorphic safety tests.

The challenger:
- uses only past-only context;
- excludes stale points;
- de-duplicates repeated observations;
- never counts as human validation.

Metamorphic tests verify that worsening:
- data quality,
- risk,
- portfolio constraint,
- event risk,
- evidence conflict

cannot increase decision aggressiveness.

Human validation remains PENDING.
