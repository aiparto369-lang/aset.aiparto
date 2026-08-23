from __future__ import annotations
from collections import Counter, defaultdict
from pathlib import Path
import json, math

LABEL_FIELDS = [
    "data_state",
    "fx_price_state",
    "fx_stress_state",
    "xau_price_state",
    "gold_premium_state",
    "coin_premium_state",
    "timing_state",
    "evidence_conflict_state",
]

def _complete_submission(obj: dict) -> bool:
    if obj.get("ambiguity") not in {"CLEAR","AMBIGUOUS","HIGHLY_AMBIGUOUS"}:
        return False
    labels=obj.get("labels") or {}
    return all(labels.get(k) not in {None,""} for k in LABEL_FIELDS)

def load_complete(dir_path: str | Path) -> dict[str,dict]:
    out={}
    for p in sorted(Path(dir_path).glob("PKT-*.json")):
        obj=json.loads(p.read_text(encoding="utf-8"))
        if _complete_submission(obj):
            out[obj["packet_id"]]=obj
    return out

def raw_agreement(pairs: list[tuple[str,str]]) -> float | None:
    if not pairs:
        return None
    return sum(a==b for a,b in pairs)/len(pairs)

def cohen_kappa(pairs: list[tuple[str,str]]) -> float | None:
    if not pairs:
        return None
    n=len(pairs)
    po=sum(a==b for a,b in pairs)/n
    ca=Counter(a for a,_ in pairs)
    cb=Counter(b for _,b in pairs)
    cats=set(ca)|set(cb)
    pe=sum((ca[c]/n)*(cb[c]/n) for c in cats)
    if abs(1-pe) < 1e-12:
        return 1.0 if abs(po-1.0)<1e-12 else 0.0
    return (po-pe)/(1-pe)

def confusion(pairs: list[tuple[str,str]]) -> dict:
    m=defaultdict(lambda: defaultdict(int))
    for a,b in pairs:
        m[a][b]+=1
    return {a:dict(row) for a,row in m.items()}

def agreement_report(a_dir: str | Path, b_dir: str | Path) -> dict:
    A=load_complete(a_dir)
    B=load_complete(b_dir)
    common=sorted(set(A)&set(B))
    report={
        "complete_A":len(A),
        "complete_B":len(B),
        "paired_complete":len(common),
        "fields":{},
        "disagreements":[]
    }
    for field in LABEL_FIELDS:
        pairs=[(A[p]["labels"][field],B[p]["labels"][field]) for p in common]
        report["fields"][field]={
            "n":len(pairs),
            "raw_agreement":raw_agreement(pairs),
            "cohen_kappa":cohen_kappa(pairs),
            "confusion":confusion(pairs)
        }
    for p in common:
        diffs={}
        for field in LABEL_FIELDS:
            av=A[p]["labels"][field]; bv=B[p]["labels"][field]
            if av!=bv:
                diffs[field]={"A":av,"B":bv}
        if diffs:
            report["disagreements"].append({
                "packet_id":p,
                "snapshot_id":A[p]["snapshot_id"],
                "differences":diffs,
                "ambiguity_A":A[p]["ambiguity"],
                "ambiguity_B":B[p]["ambiguity"]
            })
    return report
