from __future__ import annotations
from dataclasses import dataclass
from typing import Sequence

@dataclass(frozen=True)
class Point:
    ts: str
    value: float
    stale: bool = False
    source_id: str | None = None

VALID_STATES = {"UPTREND","DOWNTREND","RANGE","TRANSITION","UNKNOWN"}

def classify_monotonic_window(points: Sequence[Point], *, min_points: int = 3) -> str:
    """
    Conservative MVP classifier for already-normalized historical observations.
    It intentionally does NOT infer HH/HL from closes alone.

    Rules:
    - Need >= min_points usable observations.
    - Stale/carry-forward observations are excluded.
    - Duplicate timestamp/value pairs are de-duplicated.
    - Strict monotonic closes -> directional provisional state.
    - Flat/mixed sequence -> RANGE or TRANSITION.
    - Insufficient evidence -> UNKNOWN.

    IMPORTANT: this is a provisional close-sequence classifier for validation,
    not a production market-structure engine.
    """
    seen=set()
    usable=[]
    for p in points:
        if p.stale:
            continue
        key=(p.ts,float(p.value))
        if key in seen:
            continue
        seen.add(key)
        usable.append(p)

    if len(usable) < min_points:
        return "UNKNOWN"

    vals=[float(p.value) for p in usable[-min_points:]]
    if all(vals[i] < vals[i+1] for i in range(len(vals)-1)):
        return "UPTREND"
    if all(vals[i] > vals[i+1] for i in range(len(vals)-1)):
        return "DOWNTREND"

    # exact or near-flat values imply range-like behavior
    span=max(vals)-min(vals)
    base=max(abs(sum(vals)/len(vals)),1e-12)
    if span/base <= 0.0025:
        return "RANGE"

    return "TRANSITION"

def classify_from_packet(packet: dict, field: str) -> str:
    """
    field: 'usd_irr' or 'xauusd'
    Uses only past_only_context_window already bounded by as_of.
    """
    pts=[]
    for row in packet.get("past_only_context_window",[]):
        item=row.get(field)
        if not item:
            continue
        pts.append(Point(
            ts=item["observation_time"],
            value=float(item["value"]),
            stale=(item.get("freshness")=="STALE"),
            source_id=item.get("source_id")
        ))
    return classify_monotonic_window(pts)
