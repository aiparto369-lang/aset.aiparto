from __future__ import annotations
import argparse, json
from pathlib import Path

from capital_compass.decision.engine import decide
from capital_compass.audit.writer import write_audit
from capital_compass.rendering.fa import render_fa

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--decision-input", required=True)
    ap.add_argument("--output-dir", required=True)
    args = ap.parse_args()

    inp = json.loads(Path(args.decision_input).read_text(encoding="utf-8"))
    result = decide(inp)

    outdir = Path(args.output_dir)
    outdir.mkdir(parents=True, exist_ok=True)

    result_path = outdir/"decision-result.json"
    result_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    audit = write_audit(
        outdir/"audit-record.json",
        audit_id=result["audit_id"],
        decision_id=inp["decision_id"],
        snapshot_id=inp["snapshot_id"],
        decision_input=inp,
        decision_output=result
    )

    card = render_fa(inp, result)
    (outdir/"decision-card-fa.txt").write_text(card, encoding="utf-8")

    print(result_path)
    print(outdir/"audit-record.json")
    print(outdir/"decision-card-fa.txt")

if __name__ == "__main__":
    main()
