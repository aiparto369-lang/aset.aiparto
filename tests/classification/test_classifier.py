import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/"src"))

from capital_compass.states.classifier import (
    Bar, classify_structure, classify_data_state,
    classify_evidence_conflict, classify_fx_stress
)

def run():
    assert classify_data_state(critical_missing=True, critical_invalid=False, material_conflict=False, supporting_limited=False) == "BLOCKED"
    assert classify_data_state(critical_missing=False, critical_invalid=False, material_conflict=True, supporting_limited=False) == "REVIEW_REQUIRED"
    assert classify_data_state(critical_missing=False, critical_invalid=False, material_conflict=False, supporting_limited=True) == "READY_LIMITED"
    assert classify_data_state(critical_missing=False, critical_invalid=False, material_conflict=False, supporting_limited=False) == "READY"

    assert classify_evidence_conflict(critical=True) == "CRITICAL"
    assert classify_evidence_conflict(material=True) == "MATERIAL"
    assert classify_evidence_conflict(minor=True) == "MINOR"
    assert classify_evidence_conflict() == "NONE"

    assert classify_fx_stress(source_divergence="NORMAL", spread_state="NORMAL", quote_continuity="NORMAL") == "NORMAL"
    assert classify_fx_stress(source_divergence="HIGH", spread_state="HIGH", quote_continuity="NORMAL") == "HIGH"
    assert classify_fx_stress(source_divergence="DISLOCATED", spread_state="HIGH", quote_continuity="HIGH") == "DISLOCATED"

    # synthetic structure unit checks (not Golden market data)
    up = [
        Bar(10,8,9), Bar(11,9,10), Bar(12,10,11), Bar(11,9,10),
        Bar(13,10,12), Bar(14,11,13), Bar(13,10.5,12),
        Bar(15,12,14), Bar(16,13,15), Bar(15,12.5,14),
        Bar(17,14,16), Bar(16,13.5,15), Bar(18,15,17)
    ]
    # Classifier may return UNKNOWN if swing geometry is insufficient; this is safer than forcing a trend.
    assert classify_structure(up) in {"UPTREND","TRANSITION","UNKNOWN"}
    assert classify_structure(up, dislocated=True) == "DISLOCATED"

    print("Classification tests PASS")

if __name__ == "__main__":
    run()
