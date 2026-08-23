# Pilot Series 002–010 — Adversarial Review

## Scope
Nine historical, source-backed pilot records were added to test repeated ingestion, state transitions and decision stability.

## Core finding
The series does **not** justify a calibrated premium classifier yet.

Observed 18K observed-vs-implied premium fractions in these nine records:
- minimum: -4.28%
- median: -3.32%
- maximum: -1.24%

These values are retained as raw derived evidence only. The system does not convert them to LOW/NORMAL/HIGH because the sample is too small and not regime-representative.

## What changed versus Pilot 001
- repeated historical records now exist;
- provisional FX/XAU direction states can be exercised;
- weekend/closed-market carry-forward behavior is explicitly represented;
- decision stability can be checked across multiple historical conditions.

## What remains deliberately UNKNOWN
- FX stress: no comparable historical bid/ask / dispersion series;
- Timing: no validated setup geometry dataset;
- Premium bucket: no calibrated baseline;
- Portfolio constraint: no investor profile;
- true independent FX confirmation: historical records are still single-source.

## Adversarial conclusions
1. **PASS — no fabricated second FX source.**
2. **PASS — weekend XAU carry-forward is not misrepresented as same-day spot.**
3. **PASS — premium values are stored but not prematurely bucketed.**
4. **PASS — UNKNOWN risk/portfolio context does not become artificial confidence.**
5. **LIMITATION — historical direction labeling here is provisional and should not be promoted to Golden labels without human A/B adjudication.**
6. **LIMITATION — this series is useful for pipeline/transition testing, not for claiming investment performance.**

## Release decision
`SHADOW / VALIDATION ONLY`

No Production promotion is warranted from these records alone.
