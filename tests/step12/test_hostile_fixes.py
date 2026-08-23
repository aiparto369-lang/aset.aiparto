from copy import deepcopy
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from capital_compass.decision.engine import decide
from capital_compass.validation.decision_contract import validate_decision_result
from capital_compass.market_structure.stress import calibrate_stress, classify_stress
from capital_compass.market_structure.ohlc import Bar, pivots, classify, detect_retest

BASE = {
    "decision_id": "DEC-S12",
    "snapshot_id": "SNAP-S12",
    "asset": "IRAN_GOLD",
    "instrument": "GOLD_18K",
    "horizon": "TACTICAL",
    "states": {
        "data_state": "READY",
        "fx_price": "UPTREND",
        "xau_price": "UPTREND",
        "gold_premium": "NORMAL",
        "coin_premium": "NORMAL",
        "fx_stress": "NORMAL",
        "timing": "SETUP_CONFIRMED",
        "evidence_conflict": "NONE",
    },
    "constraints": {"risk": "NONE", "portfolio": "NONE", "event": "NONE"},
    "existing_position": "NONE",
}


def run():
    r = decide(deepcopy(BASE))
    assert r["preferred_action"] == "ACCUMULATE"
    assert validate_decision_result(r)

    x = deepcopy(BASE); x["constraints"]["risk"] = "UNKNOWN"
    assert decide(x)["preferred_action"] == "WAIT"

    x = deepcopy(BASE); x["constraints"]["portfolio"] = "UNKNOWN"
    assert decide(x)["preferred_action"] == "WAIT"

    x = deepcopy(BASE); x["constraints"]["risk"] = "REDUCE_REQUIRED"; x["existing_position"] = "MODERATE"
    assert decide(x)["preferred_action"] == "REDUCE"

    x = deepcopy(BASE); x["constraints"]["portfolio"] = "REDUCE"; x["existing_position"] = "LARGE"
    assert decide(x)["preferred_action"] == "REDUCE"

    x = deepcopy(BASE); x["constraints"]["event"] = "BLOCK"
    r = decide(x)
    assert r["preferred_action"] == "WAIT"
    assert not any(a in {"ACCUMULATE", "STAGED_ENTRY", "TACTICAL_ENTRY"} for a in r["allowed_actions"])

    x = deepcopy(BASE); x["constraints"]["risk"] = "ENTRY_LIMIT"
    assert decide(x)["preferred_action"] == "WAIT"

    x = deepcopy(BASE); x["constraints"]["risk"] = "SIZE_LIMIT"
    r = decide(x)
    assert r["preferred_action"] == "STAGED_ENTRY" and r["size_capability"] == "SMALL"

    x = deepcopy(BASE); x["states"]["data_state"] = "READY_LIMITED"
    assert decide(x)["preferred_action"] != "ACCUMULATE"

    cal = calibrate_stress([10, 11, 12], [5, 6, 7], min_samples=30)
    assert cal.status == "INSUFFICIENT_SAMPLE"
    assert classify_stress(current_spread_bps=200, source_quotes=[100, 101], calibration=cal)["state"] == "UNKNOWN"

    def B(i, c):
        return Bar(f"2026-01-{i:02d}T00:00:00+00:00", c, c + .4, c - .4, c)

    bars = [B(i, c) for i, c in enumerate([10,12,11,13,12,14,13,15,14,16,15,17,16], 1)]
    ps = pivots(bars, left=1, right=1)
    assert ps and all(p.confirmed_index > p.index and p.confirmed_at != p.ts for p in ps)

    ms = classify(bars, left=1, right=1)
    try:
        detect_retest(bars, ms, None)
        raise AssertionError("missing tolerance must fail")
    except ValueError:
        pass

    bad = decide(deepcopy(BASE)); bad["preferred_action"] = "EXIT"
    try:
        validate_decision_result(bad)
        raise AssertionError("preferred action outside allowed set must fail")
    except ValueError:
        pass

    print("Step12 hostile-fix tests PASS")


if __name__ == "__main__":
    run()
