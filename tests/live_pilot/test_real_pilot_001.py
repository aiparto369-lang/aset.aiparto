import sys, json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/"src"))
from capital_compass.decision.engine import decide

def run():
    p = ROOT/"fixtures"/"live"/"pilot-001"
    inp = json.loads((p/"decision-input.json").read_text(encoding="utf-8"))
    out = decide(inp)

    # No false certainty
    assert inp["states"]["fx_price"] == "UNKNOWN"
    assert inp["states"]["xau_price"] == "UNKNOWN"
    assert inp["states"]["gold_premium"] == "UNKNOWN"

    # Limited data cannot produce aggressive action.
    assert out["preferred_action"] in {"WAIT","INSUFFICIENT_EDGE"}
    assert "ACCUMULATE" not in out["allowed_actions"]

    # Derived premium value exists but is not prematurely bucketed.
    snap = json.loads((p/"snapshot.json").read_text(encoding="utf-8"))
    premium = snap["derived"]["gold_premium"]["value"]
    assert -0.03 < premium < 0.03

    print("Real pilot record 001 tests PASS")

if __name__ == "__main__":
    run()
