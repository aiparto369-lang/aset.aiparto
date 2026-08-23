# Step 7 — Historical Pilot Series 002–010

This step adds nine source-backed historical pilot records to exercise:
- repeated snapshot construction,
- state transitions,
- weekend/closed-market carry-forward,
- premium-history accumulation,
- deterministic decision stability.

These records are **validation records**, not live recommendations and not Golden labels.

Next technical gate:
1. human A/B labeling of these records without seeing system outputs;
2. adjudication;
3. compare system state labels vs human labels;
4. expand premium history substantially before any LOW/NORMAL/HIGH thresholds;
5. add a true independent historical/real-time FX route;
6. add historical bid/ask or spread observations for stress calibration.
