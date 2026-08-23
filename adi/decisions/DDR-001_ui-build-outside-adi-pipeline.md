# DDR-001 — UI build performed outside the ADI pipeline

**Raised under:** `CONSTITUTION.md` §6 Rule §52 (No Silent Simplification)
**Date:** 2026-08-23
**Status:** LOGGED — deviation active

## Conflict

The user directed that the Capital Compass UI be built using
`artificial-design-director` (ADI). ADI v0.1.0 cannot build a UI:

| Pipeline stage needed | Owning module | Status |
|---|---|---|
| 19 Taste / Art Direction | `taste/taste-engine.md` | NOT IMPLEMENTED (Phase 4) |
| 20 Design System | `design-system/token-architecture.md` | NOT IMPLEMENTED (Phase 5) |
| 21 Platform-neutral UI IR | `build-adapters/ui-ir.schema.md` | NOT IMPLEMENTED (Phase 8) |
| 22-23 Platform Adapter + Build | `build-adapters/<platform>/**` | NOT IMPLEMENTED (Phase 8) |

`SKILL.md` Status states plainly: *"This skill cannot currently take a real design
request end-to-end"*, and `pipeline.md` §3 requires a hard stop with an explicit
NOT IMPLEMENTED report rather than an improvised substitute.

## Reason for deviating

The user has a live commercial deadline and explicitly reaffirmed the build should
proceed. Halting entirely would deliver nothing. Rule §52 permits deviation from a
locked decision provided it is logged rather than performed silently — this DDR is
that log.

## Resolution

1. Stage 6 (Knowledge Routing) — the one stage with a Phase 1 implementation — was
   genuinely executed. Output: `adi/load-manifest-001.json`.
2. The High-Risk INVARIANT it produced **is enforced** (see Impact below). This is
   Tier 2 of the §3 priority ladder and is the one part of ADI in real force here.
3. Stages 1-5 and 7-28 were NOT run. No output of theirs is simulated, and no
   ADI stamp of any kind is applied to the artifact.
4. The UI is therefore built on the operator's own design judgement. It is
   explicitly **NOT** an ADI-generated artifact and must not be described as one.

## Impact

- The artifact carries `risk_level: High-Risk` and `no_autonomous_release: true`
  (`risk/high-risk-ui-policy.md` §5, `CONSTITUTION.md` §5). It **cannot be treated as
  released** until a Human Review event is logged by the user.
- Per Rule §53 the artifact's status is `DEFINED / NOT VERIFIED` — never VERIFIED,
  PASS, COMPLETE, or SHIPPED.
- When ADI Phases 4-8 ship, this UI should be re-run through the real pipeline and
  this DDR closed.

## Verification

Inspection only. Checked against `SKILL.md` Status, `pipeline.md` §2 table,
`risk/high-risk-ui-policy.md` §4-5, and `CONSTITUTION.md` §3/§5/§6.
