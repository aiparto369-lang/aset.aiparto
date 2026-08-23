from __future__ import annotations
import json
from pathlib import Path
from capital_compass.validation.structure_challenger import classify_from_packet

def build_report(root: str | Path) -> dict:
    root=Path(root)
    packet_dir=root/"labeling"/"packets"/"A"
    pilot_root=root/"fixtures"/"live"/"pilot-series-002-010"

    system_by_snapshot={}
    for p in sorted(pilot_root.glob("pilot-*")):
        inp=json.loads((p/"decision-input.json").read_text(encoding="utf-8"))
        system_by_snapshot[inp["snapshot_id"]]=inp["states"]

    rows=[]
    for fp in sorted(packet_dir.glob("PKT-*.json")):
        packet=json.loads(fp.read_text(encoding="utf-8"))
        sid=packet["snapshot_id"]
        challenger_fx=classify_from_packet(packet,"usd_irr")
        challenger_xau=classify_from_packet(packet,"xauusd")
        system=system_by_snapshot[sid]
        rows.append({
            "packet_id":packet["packet_id"],
            "snapshot_id":sid,
            "as_of":packet["as_of"],
            "system_fx":system["fx_price"],
            "challenger_fx":challenger_fx,
            "fx_match":system["fx_price"]==challenger_fx,
            "system_xau":system["xau_price"],
            "challenger_xau":challenger_xau,
            "xau_match":system["xau_price"]==challenger_xau,
            "note":"Challenger uses past-only close sequences; not a Golden human label."
        })

    return {
        "report_version":"0.1.0",
        "validation_type":"CHALLENGER_ONLY_NOT_HUMAN",
        "rows":rows,
        "summary":{
            "n":len(rows),
            "fx_matches":sum(r["fx_match"] for r in rows),
            "xau_matches":sum(r["xau_match"] for r in rows),
            "fx_disagreements":sum(not r["fx_match"] for r in rows),
            "xau_disagreements":sum(not r["xau_match"] for r in rows),
        }
    }

if __name__=="__main__":
    import sys
    root=Path(sys.argv[1]) if len(sys.argv)>1 else Path(".")
    report=build_report(root)
    out=root/"reports"/"step10"/"challenger-comparison.json"
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    print(out)
    print(json.dumps(report["summary"],ensure_ascii=False))
