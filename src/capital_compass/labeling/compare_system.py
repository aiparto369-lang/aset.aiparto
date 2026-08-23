from __future__ import annotations
from pathlib import Path
import json

FIELD_MAP = {
    "data_state":"data_state",
    "fx_price_state":"fx_price",
    "fx_stress_state":"fx_stress",
    "xau_price_state":"xau_price",
    "gold_premium_state":"gold_premium",
    "coin_premium_state":"coin_premium",
    "timing_state":"timing",
    "evidence_conflict_state":"evidence_conflict",
}

def compare(adjudication_file, pilot_series_root):
    adj=json.loads(Path(adjudication_file).read_text(encoding="utf-8"))
    # This function intentionally only uses adjudicated final labels.
    by_snap={}
    for item in adj.get("items",[]):
        finals=item.get("adjudication",{}).get("final_labels") or {}
        if finals:
            by_snap[item["snapshot_id"]]=finals

    rows=[]
    for p in sorted(Path(pilot_series_root).glob("pilot-*")):
        inp=json.loads((p/"decision-input.json").read_text(encoding="utf-8"))
        human=by_snap.get(inp["snapshot_id"])
        if not human:
            continue
        diffs={}
        for hfield,sfield in FIELD_MAP.items():
            if hfield in human and human[hfield] != inp["states"][sfield]:
                diffs[hfield]={"human":human[hfield],"system":inp["states"][sfield]}
        rows.append({
            "snapshot_id":inp["snapshot_id"],
            "differences":diffs,
            "match":not bool(diffs)
        })
    return rows
