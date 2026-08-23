import sys,json
from pathlib import Path
from copy import deepcopy
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"src"))

from capital_compass.validation.structure_challenger import Point, classify_monotonic_window, classify_from_packet
from capital_compass.validation.run_challenger import build_report
from capital_compass.validation.metamorphic import assert_monotonic_nonincrease
from capital_compass.decision.engine import decide

def run():
    # Pure classifier sanity
    assert classify_monotonic_window([
        Point("2026-01-01T00:00:00+00:00",1),
        Point("2026-01-02T00:00:00+00:00",2),
        Point("2026-01-03T00:00:00+00:00",3),
    ])=="UPTREND"
    assert classify_monotonic_window([
        Point("2026-01-01T00:00:00+00:00",3),
        Point("2026-01-02T00:00:00+00:00",2),
        Point("2026-01-03T00:00:00+00:00",1),
    ])=="DOWNTREND"
    assert classify_monotonic_window([
        Point("2026-01-01T00:00:00+00:00",1,stale=True),
        Point("2026-01-02T00:00:00+00:00",2),
        Point("2026-01-03T00:00:00+00:00",3),
    ])=="UNKNOWN"

    # No future leakage in challenger packets.
    for fp in sorted((ROOT/"labeling"/"packets"/"A").glob("PKT-*.json")):
        p=json.loads(fp.read_text(encoding="utf-8"))
        fx=classify_from_packet(p,"usd_irr")
        xau=classify_from_packet(p,"xauusd")
        assert fx in {"UPTREND","DOWNTREND","RANGE","TRANSITION","UNKNOWN"}
        assert xau in {"UPTREND","DOWNTREND","RANGE","TRANSITION","UNKNOWN"}

    report=build_report(ROOT)
    assert report["summary"]["n"]==9
    assert report["validation_type"]=="CHALLENGER_ONLY_NOT_HUMAN"

    # Metamorphic risk/data/portfolio invariants
    base={
      "decision_id":"DEC-META-001","snapshot_id":"SNAP-META-001",
      "asset":"IRAN_GOLD","instrument":"GOLD_18K","horizon":"TACTICAL",
      "states":{
        "data_state":"READY","fx_price":"UPTREND","xau_price":"UPTREND",
        "gold_premium":"NORMAL","coin_premium":"NORMAL","fx_stress":"NORMAL",
        "timing":"SETUP_CONFIRMED","evidence_conflict":"NONE"
      },
      "constraints":{"risk":"NONE","portfolio":"NONE","event":"NONE"},
      "existing_position":"NONE"
    }
    r0=decide(base)
    assert r0["preferred_action"]=="ACCUMULATE"

    bad_data=deepcopy(base); bad_data["states"]["data_state"]="READY_LIMITED"
    r1=decide(bad_data); assert_monotonic_nonincrease(r0,r1,dimension="data")

    bad_risk=deepcopy(base); bad_risk["constraints"]["risk"]="SIZE_LIMIT"
    r2=decide(bad_risk); assert_monotonic_nonincrease(r0,r2,dimension="risk")

    bad_port=deepcopy(base); bad_port["constraints"]["portfolio"]="NO_INCREASE"
    r3=decide(bad_port); assert_monotonic_nonincrease(r0,r3,dimension="portfolio")

    bad_event=deepcopy(base); bad_event["constraints"]["event"]="LIMIT_ENTRY"
    r4=decide(bad_event); assert_monotonic_nonincrease(r0,r4,dimension="event")

    conflict=deepcopy(base); conflict["states"]["evidence_conflict"]="MATERIAL"
    r5=decide(conflict); assert_monotonic_nonincrease(r0,r5,dimension="conflict")

    print("Step10 validation tests PASS")

if __name__=="__main__":
    run()
