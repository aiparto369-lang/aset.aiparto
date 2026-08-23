import sys,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"src"))
from capital_compass.decision.engine import decide

def run():
    base=ROOT/"fixtures"/"live"/"pilot-series-002-010"
    pilots=sorted([p for p in base.glob("pilot-*") if p.is_dir()])
    assert len(pilots)==9

    for p in pilots:
        snap=json.loads((p/"snapshot.json").read_text(encoding="utf-8"))
        inp=json.loads((p/"decision-input.json").read_text(encoding="utf-8"))
        out=decide(inp)

        # No premature premium classification.
        assert inp["states"]["gold_premium"]=="UNKNOWN"

        # No stress/timing fabrication.
        assert inp["states"]["fx_stress"]=="UNKNOWN"
        assert inp["states"]["timing"]=="UNKNOWN"

        # READY_LIMITED should never produce aggressive ACCUMULATE under current engine.
        assert out["preferred_action"] != "ACCUMULATE"

        # Any weekend XAU carry-forward is explicit in source limitations.
        xau=snap["evidence"]["xauusd"][0]
        if xau["quality"]["freshness"]=="STALE":
            assert any("carry-forward" in s.lower() for s in xau["limitations"])

    print("Pilot series 002-010 tests PASS")

if __name__=="__main__":
    run()
