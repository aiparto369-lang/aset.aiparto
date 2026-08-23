# Step 12 — Hostile Architecture Audit & Corrections

This step deliberately stops feature expansion and attacks existing logic.

Critical defects fixed:
1. UNKNOWN risk/portfolio could still lead to strong new exposure.
2. REDUCE_REQUIRED / portfolio REDUCE did not enforce reduction.
3. Event BLOCK was not a true new-risk block.
4. FX stress used arbitrary universal bps thresholds.
5. Retest used an arbitrary universal 0.3% tolerance.
6. Pivot look-ahead control existed only in prose; pivots lacked confirmation-time metadata.
7. preferred_action was not runtime-enforced to belong to allowed_actions.

Corrections:
- semantic constraint governor added;
- unknown suitability/risk now caps new exposure;
- reduction constraints now force reduction when a position exists;
- stress now requires robust Median/MAD calibration and fails closed before calibration;
- retest tolerance must be externally calibrated/configured;
- every pivot now stores confirmed_index and confirmed_at;
- runtime decision cross-field invariant added.

No new agent, asset class, forecasting model, score, or autonomous execution layer was added.

Remaining blockers are empirical, not architectural:
- independent human A/B labeling;
- licensed live XAU;
- independent comparable USD/IRR route;
- spread/source-dispersion history;
- larger premium/regime dataset;
- out-of-sample validation;
- shadow operation.

Release remains BLOCKED. Architecture expansion is frozen.
