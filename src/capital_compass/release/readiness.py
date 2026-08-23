from pathlib import Path
import json
REQUIRED=["human_ab_validation","live_xau_rights","independent_fx_route","stress_baseline_data","premium_regime_dataset","out_of_sample_validation","shadow_run"]
PASS={"PASS","APPROVED","COMPLETE","READY","VALIDATED","CLEARED"}
def evaluate(gate_file):
    d=json.loads(Path(gate_file).read_text(encoding="utf-8")); ext=d.get("remaining_external_gates",{})
    gates=[]
    for n in REQUIRED:
        s=str(ext.get(n,"MISSING")).upper(); gates.append({"name":n,"status":s,"blocking":s not in PASS})
    blocked=sum(g["blocking"] for g in gates)
    return {"software_core_status":d.get("software_core_status","UNKNOWN"),"production_release":"BLOCKED" if blocked else "ELIGIBLE_FOR_CONTROLLED_RELEASE","blocking_gate_count":blocked,"gates":gates,"rule":"No external gate may be replaced by model confidence or documentation."}
