# Pilot Record 001 — Adversarial Review

## Observed data
- USD/IRR free-market observation (TGJU): **1,927,000 IRR/USD**
- Gold 18K (TGJU): **210,360,000 IRR/gram**
- Emami coin (TGJU): **2,090,200,000 IRR**
- XAU/USD latest observed daily close (Investing.com, Aug 21): **4,603.56 USD/oz**

## Derived
- Implied 18K value from XAU × USD/IRR × 0.75: **213,908,404.28 IRR/gram**
- Observed-vs-implied difference: **-1.66%**

## Why the system does NOT label this as a strong opportunity
1. Only one exact parsed USD/IRR market observation is available in the record.
2. Bonbast confirms it is a live free-market IRR source, but numeric USD values were not exposed in the parsed page; they were not invented.
3. XAU input is the latest daily close from Aug 21, not a live executable quote.
4. A single current FX quote and one XAU close are insufficient to establish market structure.
5. Premium classification is left `UNKNOWN` because no validated historical/regime baseline exists.
6. Portfolio risk and existing exposure are unknown.

## Decision
The rule engine returns: **INSUFFICIENT_EDGE**.

This is desirable. A less disciplined system could incorrectly turn today's +1.74% USD move or +5.96% domestic 18K move into a trend call. Capital Compass refuses to do so without structure and cross-validation.

## Adversarial conclusion
**PASS with limitations.** The system preserved uncertainty rather than manufacturing state certainty. The next required evidence is:
- a second exact USD/IRR observation with comparable semantics,
- a live/approved XAU feed or sufficient price-bar history,
- bid/ask or spread data for stress classification,
- historical premium baseline,
- portfolio context for personalized sizing.
