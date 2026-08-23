from __future__ import annotations
from hashlib import sha256
import json
from datetime import datetime, timezone
from pathlib import Path

def _hash(obj: dict) -> str:
    payload = json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",",":")).encode("utf-8")
    return sha256(payload).hexdigest()

def write_audit(path: str | Path, *, audit_id: str, decision_id: str, snapshot_id: str,
                decision_input: dict, decision_output: dict,
                policy_versions: dict | None = None,
                model_versions: dict | None = None,
                notes: list[str] | None = None) -> dict:
    record = {
        "audit_id": audit_id,
        "decision_id": decision_id,
        "snapshot_id": snapshot_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "policy_versions": policy_versions or {
            "data":"0.1.0","risk":"0.1.0","decision":"0.1.0","governance":"0.1.0"
        },
        "model_versions": model_versions or {
            "decision_engine":"0.1.0",
            "state_classifier":"0.1.0"
        },
        "input_hash": _hash(decision_input),
        "output_hash": _hash(decision_output),
        "notes": notes or []
    }
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    return record
