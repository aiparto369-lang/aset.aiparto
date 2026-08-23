from __future__ import annotations
from datetime import datetime, timezone

def parse_dt(s: str) -> datetime:
    dt = datetime.fromisoformat(s.replace("Z","+00:00"))
    if dt.tzinfo is None:
        raise ValueError("timestamp must be timezone-aware")
    return dt.astimezone(timezone.utc)

def validate_temporal(evidence: dict, as_of: str, max_age_seconds: int) -> str:
    obs = parse_dt(evidence["observation_time"])
    ref = parse_dt(as_of)
    age = (ref - obs).total_seconds()
    if age < -1:
        return "INVALID_FUTURE"
    if age <= max_age_seconds:
        return "CURRENT"
    return "STALE"

def group_independent_origins(evidence: list[dict]) -> dict[str, list[str]]:
    groups = {}
    for ev in evidence:
        origin = ev["source"]["origin_id"]
        groups.setdefault(origin, []).append(ev["evidence_id"])
    return groups

def quote_semantics_compatible(a: dict, b: dict) -> bool:
    # BID and ASK are intentionally not treated as same semantic point.
    return (
        a["variable_id"] == b["variable_id"]
        and a["unit"] == b["unit"]
        and a.get("quote_type") == b.get("quote_type")
    )

def detect_basic_conflict(evidence: list[dict]) -> str:
    """
    Does not invent a numeric conflict threshold.
    It only flags semantic incompatibility or multiple origins for later comparison.
    """
    if not evidence:
        return "CRITICAL"
    variable_ids = {e["variable_id"] for e in evidence}
    units = {e["unit"] for e in evidence}
    if len(variable_ids) > 1 or len(units) > 1:
        return "CRITICAL"

    quote_types = {e.get("quote_type") for e in evidence}
    if len(quote_types) > 1:
        return "MATERIAL"

    origins = group_independent_origins(evidence)
    if len(origins) == 1 and len(evidence) > 1:
        return "MINOR"  # duplicate/syndicated, not independent confirmation
    return "NONE"
