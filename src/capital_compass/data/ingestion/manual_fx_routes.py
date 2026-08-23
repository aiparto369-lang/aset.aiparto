from __future__ import annotations
from capital_compass.data.collectors.manual import ManualCollector
from capital_compass.data.normalization.normalizer import normalize_observation

ROUTES = {
    "IRAN-FX-MANUAL-TGJU": {
        "source_id":"SRC-TGJU",
        "source_class":"MARKET_OBSERVATION"
    },
    "IRAN-FX-MANUAL-BONBAST": {
        "source_id":"SRC-BONBAST",
        "source_class":"MARKET_OBSERVATION"
    }
}

def ingest_manual_fx(route_id: str, record: dict, evidence_id: str) -> dict:
    if route_id not in ROUTES:
        raise KeyError(f"unknown route_id: {route_id}")
    route = ROUTES[route_id]
    record = dict(record)
    record["source_id"] = route["source_id"]
    raw = ManualCollector.from_record(record)
    ev = normalize_observation(
        raw,
        evidence_id=evidence_id,
        source_class=route["source_class"],
        materiality="M1"
    )
    ev["limitations"] = [
        f"Pilot manual observation via {route_id}; automation rights unresolved.",
        "Requires semantics/time/source-origin cross-check."
    ]
    return ev
