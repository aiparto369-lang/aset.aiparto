from __future__ import annotations
import json, sys
from pathlib import Path
from capital_compass.labeling.agreement import agreement_report
from capital_compass.labeling.adjudication import build_queue

def main(root="."):
    root=Path(root)
    a=root/"labeling"/"submissions"/"A"
    b=root/"labeling"/"submissions"/"B"
    report=agreement_report(a,b)
    out=root/"labeling"/"reports"/"agreement-report.json"
    out.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    build_queue(a,b,root/"labeling"/"adjudication"/"queue.json")
    print(out)
    print(f"paired_complete={report['paired_complete']}")

if __name__=="__main__":
    main(sys.argv[1] if len(sys.argv)>1 else ".")
