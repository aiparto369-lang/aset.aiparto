from __future__ import annotations
from copy import deepcopy
from hashlib import sha256
import json

REQUIRED_BUCKETS = ["xauusd","usd_irr","gold_18k","melted_gold","emami_coin"]

def canonical_hash(obj: dict) -> str:
    payload = json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",",":")).encode("utf-8")
    return sha256(payload).hexdigest()

def build_snapshot(snapshot_id: str, as_of: str, evidence_by_bucket: dict,
                   derived: dict | None = None, events: list | None = None,
                   iran_session: str = "UNKNOWN", xau_session: str = "UNKNOWN") -> tuple[dict,str]:
    buckets = {k: deepcopy(evidence_by_bucket.get(k, [])) for k in REQUIRED_BUCKETS}
    snapshot = {
        "snapshot_id": snapshot_id,
        "as_of": as_of,
        "immutable": True,
        "market_state": {
            "iran_session": iran_session,
            "xau_session": xau_session
        },
        "evidence": buckets,
        "derived": {
            "implied_gold_value": None,
            "gold_premium": None,
            "coin_premium": None,
            **(derived or {})
        },
        "events": list(events or [])
    }
    return snapshot, canonical_hash(snapshot)

def assert_immutable(snapshot: dict, expected_hash: str) -> None:
    actual = canonical_hash(snapshot)
    if actual != expected_hash:
        raise RuntimeError("snapshot integrity violation: content changed after freeze")
