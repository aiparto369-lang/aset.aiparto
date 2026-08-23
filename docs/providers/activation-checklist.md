# Provider Activation Checklist v0.1

## XAUUSD Candidate A — Alpha Vantage
**Status:** selected as preferred pilot candidate; disabled by default.

Before activation:
- [ ] API key acquired.
- [ ] Exact GOLD_SILVER_SPOT payload captured and contract-tested.
- [ ] Observation timestamp semantics confirmed.
- [ ] Quote semantics confirmed (spot/last vs bid/ask).
- [ ] Business/commercial-use agreement confirmed in writing.
- [ ] Storage/retention rights confirmed.
- [ ] Redistribution/display rights confirmed if user-facing raw values are shown.
- [ ] Rate limits documented.
- [ ] Failure/timeout behavior tested.
- [ ] Secondary cross-check configured.
- [ ] Source independence checked.

## XAUUSD Candidate B — Metals-API
**Status:** challenger/fallback candidate; disabled by default.

Before activation:
- [ ] Paid plan selected if used beyond testing.
- [ ] Competition restriction reviewed against Capital Compass product design.
- [ ] Commercial-use/retention rights accepted.
- [ ] Bid/ask payload contract-tested.
- [ ] Inverse-rate conversion verified using live response semantics.
- [ ] Timestamp/update frequency confirmed for selected plan.
- [ ] Soft-limit/overage controls disabled or budget-capped as appropriate.
- [ ] Cross-check independence assessed.

## USD/IRR Pilot Route A — TGJU manual observation
- [ ] Human operator records quote type exactly.
- [ ] Observation timestamp captured.
- [ ] Source page/reference captured.
- [ ] IRR/Toman unit captured explicitly.
- [ ] No automated scraping in pilot unless terms/access are cleared.

## USD/IRR Pilot Route B — Bonbast manual observation
Same controls as above.

## Activation invariant
A provider being technically reachable does **not** mean it is approved.
`TECHNICAL_PASS && RIGHTS_PASS && SEMANTIC_PASS && FAILURE_PASS` are all required.
