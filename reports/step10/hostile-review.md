# Step 10 — Hostile Validation Review

## Added
A second independent rule-based challenger re-evaluates FX/XAU directional state using only past-only context.

It is explicitly **not** a human label.

## Comparison
- Records: 9
- FX matches: 9
- FX disagreements: 0
- XAU matches: 9
- XAU disagreements: 0

## Hostile findings
1. Close sequence is not true HH/HL structure — acknowledged. Challenger is provisional only.
2. Stale XAU carry-forward can fake trend persistence — stale points are excluded.
3. Duplicates can inflate sample size — duplicate timestamp/value pairs are removed.
4. Worse data/risk/portfolio/event conditions must never increase action aggressiveness — metamorphic tests PASS.
5. Challenger output must not masquerade as human validation — enforced.
6. Sample remains too small for premium/stress/tail calibration.

## Release Gate
**SHADOW / VALIDATION ONLY**

Production promotion remains blocked until:
- independent human A/B labeling,
- larger sample,
- stronger market-structure data,
- real spread/microstructure data,
- premium baseline calibration.
