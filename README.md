# Capital Compass v3 — Gold/FX Implementation Specification

این بسته اولین implementation-ready baseline برای Vertical Slice طلا / USD-IRR است.

## محتوا

- `contracts/evidence.schema.json`
- `contracts/snapshot.schema.json`
- `contracts/state.schema.json`
- `contracts/decision-input.schema.json`
- `contracts/decision-result.schema.json`
- `contracts/audit-record.schema.json`
- `fixtures/golden/` — 50 baseline machine-readable cases
- `fixtures/manifest.json`
- `tests/reference_rules.py` — reference deterministic rule engine
- `tests/validate_fixtures.py` — schema + smoke validation

## اصول معماری

1. LLM source of truth نیست.
2. Raw market data مستقیم وارد Decision Engine نمی‌شود.
3. Decision بر اساس Structured State اجرا می‌شود.
4. Hard gates بیرون از LLM اجرا می‌شوند.
5. Snapshot بعد از تصمیم immutable است.
6. `UNKNOWN != NEUTRAL`.
7. Data/Risk/Portfolio block قابل override توسط LLM نیست.
8. این 50 fixture فقط smoke baseline هستند، نه validation نهایی.
9. Thresholdهای عددی premium/spread/stress تا زمان calibration عمداً hard-code نشده‌اند.
10. قبل از Production، pilot → golden set → blind holdout → shadow → paper → limited production الزامی است.

## اجرای تست

```bash
pip install jsonschema
cd tests
python validate_fixtures.py
```

## نکته مهم

`reference_rules.py` مرجع اولیه برای تست contracts و invariants است، نه مدل نهایی سرمایه‌گذاری. هر تغییر در ruleها باید versioned و regression-tested باشد.


## Step 2 added — Labeling & Pilot Infrastructure

این نسخه اکنون شامل موارد زیر نیز هست:

- `contracts/label.schema.json`
- `contracts/pilot-capture.schema.json`
- `docs/labeling/labeling-manual-v0.1.0.md`
- `docs/labeling/pilot-procedure-v0.1.md`
- `src/capital_compass/states/classifier.py`
- `src/capital_compass/dataset/pilot_planner.py`
- `fixtures/pilot/capture-plan.json`
- `tests/classification/test_classifier.py`

### اصل مهم
فایل‌های Pilot در این بسته **داده واقعی بازار نیستند**؛ فقط برنامه و Contract جمع‌آوری‌اند. Snapshot واقعی باید از Sourceهای واقعی و timestamped وارد شود. این بسته عمداً داده بازار جعل نمی‌کند.


## Step 3 added — Data Acquisition & Snapshot Pipeline

- `contracts/source-registry.schema.json`
- `config/sources.json`
- `config/variables.json`
- `src/capital_compass/data/collectors/`
- `src/capital_compass/data/normalization/`
- `src/capital_compass/data/validation/`
- `src/capital_compass/data/snapshot/`
- `src/capital_compass/calculations/gold.py`
- `tests/data_pipeline/`
- `docs/data/step3-data-pipeline.md`

این مرحله عمداً endpoint یا داده‌ی بازار جعل نمی‌کند. Sourceهای واقعی باید پس از بررسی semantics، دسترسی، licensing و failure behavior متصل شوند.


## Step 4 added — Provider Selection & Live Ingestion

- `config/provider-selection.json`
- `.env.providers.example`
- `src/capital_compass/data/providers/alpha_vantage.py`
- `src/capital_compass/data/providers/metals_api.py`
- `src/capital_compass/data/ingestion/provider_to_evidence.py`
- `src/capital_compass/data/ingestion/manual_fx_routes.py`
- `src/capital_compass/data/ingestion/live_snapshot.py`
- `tests/providers/test_provider_adapters.py`
- `docs/providers/activation-checklist.md`
- `docs/providers/live-ingestion-runbook.md`

Both XAU adapters are intentionally disabled until credentials **and** data-use rights are confirmed. USD/IRR uses dual controlled manual pilot routes until automation rights are cleared.


## Step 5 added — End-to-End Pilot Decision Pipeline

- `src/capital_compass/decision/engine.py`
- `src/capital_compass/audit/writer.py`
- `src/capital_compass/rendering/fa.py`
- `src/capital_compass/orchestration/preflight.py`
- `src/capital_compass/orchestration/pilot_decision.py`
- `tests/end_to_end/test_pilot_e2e.py`
- `docs/pilot/step5-end-to-end.md`

اکنون مسیر `Structured Decision Input → Decision → Audit → Persian Decision Card` قابل اجراست. Fixture نمونه فقط برای تست است و نباید به‌عنوان داده بازار واقعی استفاده شود.


## Step 6 added — First Evidence-Backed Real Pilot Record

The repository now contains a real public-data-backed pilot record for 2026-08-22.
It is deliberately classified with substantial `UNKNOWN/READY_LIMITED` states where evidence is insufficient.

This is a feature, not a failure: no missing quote, market structure, premium baseline, or portfolio context is fabricated.


## Step 7 added — Pilot Records 002–010

Nine source-backed historical pilot records are now included under:
`fixtures/live/pilot-series-002-010/`

They are used only for transition/pipeline validation. Premium, stress and timing remain deliberately uncalibrated where evidence is insufficient.


## Step 8 added — Blind Human A/B Labeling

Nine blind packets for Labeler A and nine for Labeler B are now generated under `labeling/packets/`.
System decisions/states and future outcomes are excluded from the packets.

**No human labels are fabricated.** `labeling/status.json` remains `PENDING` until two independent human reviewers complete the submissions.


## Step 9 added — Reviewer Workflow + Blind Context Fix

A hostile review found that single-snapshot blind packets were insufficient for fair market-structure labeling. Each packet now includes a bounded past-only context window ending at `as_of`, while future data and system outputs remain hidden.

Two local reviewer UIs are included:
- `labeling/review-ui/labeler-A.html`
- `labeling/review-ui/labeler-B.html`

AI shadow labels are also included strictly as non-human workflow rehearsal and are never counted as human validation.


## Step 13 — Software Baseline Finalization

Gold/FX software architecture is frozen at `IMPLEMENTATION_BASELINE_COMPLETE`.

A release-readiness evaluator, freeze manifest, acceptance matrix, and final handoff have been added.

Further architecture work is prohibited until empirical evidence arrives from human validation, approved providers, larger calibration datasets, out-of-sample testing, or shadow operation.

## Final distribution hardening — v1.0.0

The final distributable adds deterministic package metadata (`pyproject.toml`), explicit package markers, executable Step 12/13 regression tests, and a single `tests/run_all.py` runner. Python bytecode/cache artifacts are excluded from the clean distribution.

Run the complete software-baseline suite with:

```bash
python tests/run_all.py
```

Passing the software suite does **not** change production status. External empirical gates remain authoritative.
