from __future__ import annotations
from dataclasses import asdict

SOURCE_CLASS = {
    "ALPHA_VANTAGE":"PROFESSIONAL_MARKET_DATA",
    "METALS_API":"PROFESSIONAL_MARKET_DATA",
}

SOURCE_ID = {
    "ALPHA_VANTAGE":"SRC-ALPHA-VANTAGE",
    "METALS_API":"SRC-METALS-API",
}

def quote_to_evidence(q, evidence_id: str) -> dict:
    return {
        "evidence_id": evidence_id,
        "variable_id": q.variable_id,
        "asset": "GOLD",
        "market": "GLOBAL",
        "value": q.value,
        "unit": q.unit,
        "quote_type": q.quote_type,
        "observation_time": q.observation_time,
        "retrieval_time": q.retrieval_time,
        "source": {
            "source_id": SOURCE_ID[q.provider],
            "class": SOURCE_CLASS[q.provider],
            "origin_id": q.source_origin,
            "name": q.provider,
            "uri": None
        },
        "quality": {
            "freshness": "CURRENT",
            "verification": "PARTIAL",
            "conflict": "NONE",
            "quality_class": "DQ-B"
        },
        "materiality": "M1",
        "lineage": {
            "raw_reference": q.source_origin,
            "derived": False,
            "formula_id": None,
            "formula_version": None,
            "input_evidence_ids": []
        },
        "limitations": [
            "Provider quote must be cross-checked before DQ-A.",
            "Commercial/data-use rights are governed by provider contract."
        ]
    }
