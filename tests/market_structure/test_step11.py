import sys
from pathlib import Path

R = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(R / "src"))

from capital_compass.market_structure.ohlc import Bar, classify, sanitize
from capital_compass.market_structure.premium_baseline import calibrate, classify as classify_premium
from capital_compass.market_structure.stress import calibrate_stress, classify_stress


def B(i, c, stale=False):
    return Bar(f"2026-01-{i:02d}T00:00:00+00:00", c, c + .4, c - .4, c, stale)


def run():
    # Alternating swings with rising highs/lows. left/right=1 is explicit test geometry.
    up = [B(i, c) for i, c in enumerate([10,12,11,13,12,14,13,15,14,16,15], 1)]
    a = classify(up, left=1, right=1)
    assert a.state == "UPTREND", a

    down = [B(i, c) for i, c in enumerate([20,18,19,17,18,16,17,15,16,14,15], 1)]
    b = classify(down, left=1, right=1)
    assert b.state == "DOWNTREND", b

    # Invalid and stale bars are excluded.
    assert len(sanitize([Bar("x",10,9,11,10), B(2,10,True)])) == 0

    # Premium remains fail-closed below sample gate.
    c = calibrate([-.03,-.02,-.01] * 3)
    assert c.status == "INSUFFICIENT_SAMPLE"
    assert classify_premium(-.02, c) == "UNKNOWN"

    vals = [-.03 + (i % 20) * .001 for i in range(80)]
    c2 = calibrate(vals)
    assert c2.status == "CALIBRATED"
    assert classify_premium(c2.median, c2) == "NORMAL"

    # Stress remains UNKNOWN before robust baseline calibration.
    sc = calibrate_stress([10,11,12], [4,5,6], min_samples=30)
    assert sc.status == "INSUFFICIENT_SAMPLE"
    assert classify_stress(current_spread_bps=100, source_quotes=[100,100.2], calibration=sc)["state"] == "UNKNOWN"

    # Calibrated non-degenerate synthetic baseline can produce NORMAL.
    spreads = [10 + (i % 7) for i in range(40)]
    dispersions = [4 + (i % 5) for i in range(40)]
    sc2 = calibrate_stress(spreads, dispersions, min_samples=30)
    assert sc2.status == "CALIBRATED"
    # Construct quotes with dispersion close to baseline scale.
    r = classify_stress(current_spread_bps=sc2.spread_median, source_quotes=[100,100.08], calibration=sc2)
    assert r["state"] in {"NORMAL","ELEVATED"}

    print("Step11 market-structure/calibration tests PASS")


if __name__ == "__main__":
    run()
