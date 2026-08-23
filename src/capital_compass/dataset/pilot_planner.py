from __future__ import annotations
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path

def build_plan(start: datetime, routine_count: int = 60):
    """
    Generates a capture schedule template only.
    It does not fetch market data or invent real snapshots.
    Event/stress captures must be added when they actually occur.
    """
    if start.tzinfo is None:
        start = start.replace(tzinfo=timezone.utc)

    plan = []
    t = start
    for i in range(1, routine_count+1):
        plan.append({
            "capture_id": f"CAP-R{i:03d}",
            "scheduled_for": t.isoformat(),
            "captured_at": None,
            "capture_type": "ROUTINE",
            "snapshot_file": f"fixtures/pilot/SNAP-R{i:03d}.json",
            "status": "PLANNED",
            "notes": None
        })
        # 4-hour cadence across active days is a starting operational template,
        # not a market rule.
        t += timedelta(hours=4)
    return plan

if __name__ == "__main__":
    root = Path(__file__).resolve().parents[3]
    plan = build_plan(datetime.now(timezone.utc), routine_count=60)
    out = root / "fixtures" / "pilot" / "capture-plan.json"
    out.write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")
    print(out)
