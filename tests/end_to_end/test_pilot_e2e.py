import sys, json, tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/"src"))

from capital_compass.decision.engine import decide
from capital_compass.audit.writer import write_audit
from capital_compass.rendering.fa import render_fa
from capital_compass.orchestration.preflight import check_xau_activation, PreflightBlocked

def run():
    inp = json.loads((ROOT/"fixtures"/"pilot"/"records"/"decision-input-sample.json").read_text(encoding="utf-8"))
    out = decide(inp)
    assert out["preferred_action"] == "ACCUMULATE"
    assert out["size_capability"] == "MODERATE"

    # Hard-gate monotonicity
    blocked = json.loads(json.dumps(inp))
    blocked["constraints"]["risk"] = "BLOCK"
    out2 = decide(blocked)
    assert out2["preferred_action"] == "DECISION_BLOCKED"

    noadd = json.loads(json.dumps(inp))
    noadd["constraints"]["portfolio"] = "NO_INCREASE"
    out3 = decide(noadd)
    assert out3["preferred_action"] in {"HOLD","WAIT"}
    assert "ACCUMULATE" not in out3["allowed_actions"]

    # Audit
    with tempfile.TemporaryDirectory() as td:
        p = Path(td)/"audit.json"
        rec = write_audit(
            p,
            audit_id=out["audit_id"],
            decision_id=inp["decision_id"],
            snapshot_id=inp["snapshot_id"],
            decision_input=inp,
            decision_output=out
        )
        assert p.exists()
        assert len(rec["input_hash"]) == 64
        assert len(rec["output_hash"]) == 64

    # Renderer cannot change decision
    card = render_fa(inp, out)
    assert "افزایش موقعیت" in card
    assert "متوسط" in card

    # Provider preflight fail-closed
    try:
        check_xau_activation({}, "ALPHA_VANTAGE", rights_ack=False, technical_ready=True)
        raise AssertionError("rights gate must block")
    except PreflightBlocked:
        pass

    assert check_xau_activation({}, "ALPHA_VANTAGE", rights_ack=True, technical_ready=True) is True
    print("End-to-end pilot tests PASS")

if __name__ == "__main__":
    run()
