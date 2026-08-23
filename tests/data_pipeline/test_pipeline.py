import sys, json
from pathlib import Path
from copy import deepcopy

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/"src"))

from capital_compass.data.collectors.manual import ManualCollector
from capital_compass.data.normalization.normalizer import normalize_observation
from capital_compass.data.validation.validator import (
    detect_basic_conflict, group_independent_origins, validate_temporal
)
from capital_compass.data.snapshot.builder import build_snapshot, assert_immutable
from capital_compass.calculations.gold import gold_18k_implied_irr_per_gram, premium_fraction

def run():
    raw = ManualCollector.from_record({
        "variable_id":"USD_IRR_FREE_MARKET",
        "raw_value":100000,
        "raw_unit":"TOMAN_PER_USD",
        "quote_type":"REFERENCE",
        "observation_time":"2026-08-22T10:00:00+00:00",
        "retrieval_time":"2026-08-22T10:00:05+00:00",
        "source_origin":"manual:test:fx",
        "market":"IRAN_FREE_MARKET",
        "asset":"USD_IRR"
    })
    ev = normalize_observation(
        raw, evidence_id="EV-PIPE-001",
        source_class="MARKET_OBSERVATION", materiality="M1"
    )
    assert ev["value"] == 1000000.0
    assert ev["unit"] == "IRR_PER_USD"

    # Explicit unit conversion guard
    bad = ManualCollector.from_record({
        "variable_id":"USD_IRR_FREE_MARKET",
        "raw_value":100,
        "raw_unit":"USD_PER_TROY_OUNCE",
        "quote_type":"REFERENCE",
        "observation_time":"2026-08-22T10:00:00+00:00",
        "source_origin":"manual:test:badunit",
        "market":"IRAN_FREE_MARKET",
        "asset":"USD_IRR"
    })
    try:
        normalize_observation(bad, evidence_id="EV-PIPE-002", source_class="MARKET_OBSERVATION")
        raise AssertionError("unsupported unit conversion must fail")
    except ValueError:
        pass

    # Duplicate origin does not become independent confirmation
    ev2 = deepcopy(ev)
    ev2["evidence_id"] = "EV-PIPE-003"
    assert len(group_independent_origins([ev, ev2])) == 1
    assert detect_basic_conflict([ev, ev2]) == "MINOR"

    # Different quote semantics is material, not blindly averaged
    ev3 = deepcopy(ev)
    ev3["evidence_id"] = "EV-PIPE-004"
    ev3["source"]["origin_id"] = "manual:test:fx2"
    ev3["quote_type"] = "BID"
    assert detect_basic_conflict([ev, ev3]) == "MATERIAL"

    assert validate_temporal(ev, "2026-08-22T10:05:00+00:00", 600) == "CURRENT"
    assert validate_temporal(ev, "2026-08-22T12:00:00+00:00", 600) == "STALE"

    implied = gold_18k_implied_irr_per_gram(2500.0, 1000000.0)
    assert implied > 0
    assert abs(premium_fraction(implied, implied)) < 1e-12

    snap, h = build_snapshot(
        "SNAP-PIPE-001",
        "2026-08-22T10:05:00+00:00",
        {"usd_irr":[ev]},
        iran_session="OPEN",
        xau_session="OPEN"
    )
    assert_immutable(snap, h)

    mutated = deepcopy(snap)
    mutated["market_state"]["iran_session"] = "CLOSED"
    try:
        assert_immutable(mutated, h)
        raise AssertionError("mutated snapshot must fail integrity check")
    except RuntimeError:
        pass

    print("Data pipeline tests PASS")

if __name__ == "__main__":
    run()
