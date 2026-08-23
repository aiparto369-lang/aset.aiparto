import json
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from capital_compass.release.readiness import evaluate


def run():
    gate = ROOT / "reports" / "step12" / "release-gate-v0.2.json"
    r = evaluate(gate)
    assert r["production_release"] == "BLOCKED"
    assert r["blocking_gate_count"] == 7

    data = json.loads(gate.read_text(encoding="utf-8"))
    for k in data["remaining_external_gates"]:
        data["remaining_external_gates"][k] = "PASS"
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "gate.json"
        p.write_text(json.dumps(data), encoding="utf-8")
        r2 = evaluate(p)
        assert r2["production_release"] == "ELIGIBLE_FOR_CONTROLLED_RELEASE"
        assert r2["blocking_gate_count"] == 0

    print("Step13 release-readiness tests PASS")


if __name__ == "__main__":
    run()
