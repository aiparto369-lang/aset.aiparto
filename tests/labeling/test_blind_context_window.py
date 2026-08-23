import json
from pathlib import Path
from datetime import datetime
ROOT=Path(__file__).resolve().parents[2]
def dt(s): return datetime.fromisoformat(s.replace("Z","+00:00"))
def run():
    for side in ["A","B"]:
        files=sorted((ROOT/"labeling"/"packets"/side).glob("PKT-*.json"))
        assert len(files)==9
        for fp in files:
            p=json.loads(fp.read_text(encoding="utf-8")); target=dt(p["as_of"])
            assert p["future_data_hidden"] is True and p["system_outputs_hidden"] is True
            for row in p["past_only_context_window"]:
                assert dt(row["as_of"]) <= target
                for k in ["usd_irr","xauusd","gold_18k"]:
                    v=row.get(k)
                    if v and v.get("observation_time"):
                        assert dt(v["observation_time"]) <= target
            txt=fp.read_text(encoding="utf-8")
            assert "preferred_action" not in txt
    print("Blind context-window tests PASS")
if __name__=="__main__": run()
