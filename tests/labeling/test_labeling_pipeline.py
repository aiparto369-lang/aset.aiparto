import sys,json,tempfile,shutil
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"src"))
from capital_compass.labeling.agreement import agreement_report
from capital_compass.labeling.adjudication import build_queue

def fill(path, labels, ambiguity="CLEAR"):
    obj=json.loads(path.read_text(encoding="utf-8"))
    obj["labels"].update(labels)
    obj["ambiguity"]=ambiguity
    obj["created_at"]="2026-08-22T20:50:00+00:00"
    path.write_text(json.dumps(obj,ensure_ascii=False,indent=2),encoding="utf-8")

def run():
    # Packets must hide system outputs.
    for side in ["A","B"]:
        packets=sorted((ROOT/"labeling"/"packets"/side).glob("PKT-*.json"))
        assert len(packets)==9
        for p in packets:
            obj=json.loads(p.read_text(encoding="utf-8"))
            assert obj["future_data_hidden"] is True
            assert obj["system_outputs_hidden"] is True
            txt=p.read_text(encoding="utf-8")
            assert "preferred_action" not in txt
            assert "decision-result" not in txt

    # Blank real submissions should produce zero paired-complete, not fake agreement.
    report=agreement_report(ROOT/"labeling"/"submissions"/"A",ROOT/"labeling"/"submissions"/"B")
    assert report["paired_complete"]==0

    # Synthetic unit-test-only submissions verify agreement math.
    with tempfile.TemporaryDirectory() as td:
        td=Path(td); (td/"A").mkdir(); (td/"B").mkdir()
        for side in ["A","B"]:
            src=ROOT/"labeling"/"submissions"/side/"PKT-001.json"
            shutil.copy(src,td/side/"PKT-001.json")
        labels={
            "data_state":"READY_LIMITED",
            "fx_price_state":"UNKNOWN",
            "fx_stress_state":"UNKNOWN",
            "xau_price_state":"UNKNOWN",
            "gold_premium_state":"UNKNOWN",
            "coin_premium_state":"UNKNOWN",
            "timing_state":"UNKNOWN",
            "evidence_conflict_state":"NONE"
        }
        fill(td/"A"/"PKT-001.json",labels)
        fill(td/"B"/"PKT-001.json",labels)
        r=agreement_report(td/"A",td/"B")
        assert r["paired_complete"]==1
        assert all(v["raw_agreement"]==1.0 for v in r["fields"].values())

        # Introduce disagreement to ensure queue is generated.
        obj=json.loads((td/"B"/"PKT-001.json").read_text(encoding="utf-8"))
        obj["labels"]["fx_price_state"]="TRANSITION"
        (td/"B"/"PKT-001.json").write_text(json.dumps(obj,ensure_ascii=False,indent=2),encoding="utf-8")
        q=build_queue(td/"A",td/"B",td/"queue.json")
        assert len(q)==1
        assert "fx_price_state" in q[0]["differences"]

    print("Labeling infrastructure tests PASS")

if __name__=="__main__":
    run()
