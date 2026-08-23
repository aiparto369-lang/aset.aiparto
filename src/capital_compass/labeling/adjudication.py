from __future__ import annotations
from pathlib import Path
import json
from capital_compass.labeling.agreement import agreement_report

def build_queue(a_dir, b_dir, out_path):
    report=agreement_report(a_dir,b_dir)
    queue=[]
    for d in report["disagreements"]:
        queue.append({
            "packet_id":d["packet_id"],
            "snapshot_id":d["snapshot_id"],
            "differences":d["differences"],
            "adjudication":{
                "final_labels":{},
                "rationale":None,
                "evidence_refs":[],
                "ambiguity":"AMBIGUOUS",
                "adjudicator_id":None,
                "adjudicated_at":None
            }
        })
    Path(out_path).write_text(json.dumps({
        "queue_version":"0.1.0",
        "items":queue
    },ensure_ascii=False,indent=2),encoding="utf-8")
    return queue
