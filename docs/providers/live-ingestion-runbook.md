# Live Ingestion Runbook — Pilot v0.1

## Current operating mode
The repository is now capable of live XAU provider integration, but both API adapters are **fail-closed and disabled by default**. This is intentional.

## XAU activation
After acquiring and approving a provider:

```bash
export ALPHAVANTAGE_API_KEY='...'
export CC_ENABLE_ALPHA_VANTAGE=true
python -m capital_compass.data.ingestion.live_snapshot \
  --xau-provider alpha \
  --output fixtures/live/xau-snapshot.json
```

or challenger:

```bash
export METALS_API_KEY='...'
export CC_ENABLE_METALS_API=true
python -m capital_compass.data.ingestion.live_snapshot \
  --xau-provider metals \
  --output fixtures/live/xau-snapshot.json
```

## USD/IRR pilot
Until automation rights are confirmed, collect two controlled manual observations:
- route `IRAN-FX-MANUAL-TGJU`
- route `IRAN-FX-MANUAL-BONBAST`

Each record must include:
- raw value
- raw unit
- quote type
- observation timestamp
- source origin/reference
- market/instrument semantics

Do not average conflicting quotes automatically.

## First real snapshot acceptance
A first real snapshot is acceptable only if:
- XAU quote comes from an activated provider.
- Two USD/IRR observations are captured independently.
- Units are explicit.
- Timestamps are aligned enough for the configured pilot window.
- Source conflicts are classified.
- Snapshot hash is frozen.
- Raw values are retained.
